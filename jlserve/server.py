"""FastAPI server integration for JLServe apps."""

import asyncio
import threading
from contextlib import asynccontextmanager
from typing import Callable, Optional, Type

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from jlserve.decorator import get_endpoint_methods
from jlserve.exceptions import EndpointSetupError
from jlserve.validator import get_method_input_type, get_method_output_type, validate_app

HEALTH_PATH = "/health"


def create_app(app_cls: Type, on_ready: Optional[Callable[[], None]] = None) -> FastAPI:
    """Create a FastAPI app from a JLServe app class.

    Args:
        app_cls: The app class decorated with @jlserve.app().
        on_ready: Optional callback invoked once setup() has completed and the
            server is able to serve requests. The CLI uses this to print the
            startup banner only after the model has actually loaded.

    Returns:
        A configured FastAPI application with:
        - one POST route per endpoint method
        - GET /health, which returns 200 only after setup() has completed

    Raises:
        EndpointValidationError: If the app class is invalid.
        EndpointSetupError: If the setup() method fails.
    """
    validate_app(app_cls)

    app_name = getattr(app_cls, "_jlserve_app_name", "app")
    endpoint_methods = get_endpoint_methods(app_cls)

    # Create the app instance once - shared across all endpoints
    app_instance = app_cls()

    # One model call at a time. Endpoint methods run in a worker thread so the
    # event loop stays free to answer /health during a long generation; the
    # lock keeps them from overlapping on the shared model.
    call_lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.ready = False
        # Call setup() if it exists
        if hasattr(app_instance, "setup") and callable(app_instance.setup):
            try:
                app_instance.setup()
            except Exception as e:
                raise EndpointSetupError(f"setup() failed: {e}") from e
        app.state.ready = True
        if on_ready is not None:
            on_ready()

        yield

        app.state.ready = False

    fastapi_app = FastAPI(title=app_name, lifespan=lifespan)
    fastapi_app.state.ready = False

    _register_health_route(fastapi_app)

    # Register a POST route for each endpoint method
    for method in endpoint_methods:
        _register_endpoint_route(fastapi_app, method, app_instance, call_lock)

    return fastapi_app


def _register_health_route(fastapi_app: FastAPI) -> None:
    """Register GET /health.

    Returns 200 only once setup() has completed. Before that, 503. The serverless
    platform polls this path for readiness and liveness, so it must never answer
    200 for a worker whose model is not loaded, and must keep answering while an
    endpoint call is in progress.
    """

    @fastapi_app.get(HEALTH_PATH, include_in_schema=False)
    async def health(request: Request):
        if getattr(request.app.state, "ready", False):
            return JSONResponse(status_code=200, content={"status": "ok"})
        return JSONResponse(status_code=503, content={"status": "starting"})


def _register_endpoint_route(
    fastapi_app: FastAPI,
    method: Callable,
    app_instance: object,
    call_lock: threading.Lock,
) -> None:
    """Register a POST route for an endpoint method.

    Args:
        fastapi_app: The FastAPI application to register the route on.
        method: The endpoint method to create a route for.
        app_instance: The shared app instance to call methods on.
        call_lock: Lock serialising endpoint calls to one at a time.
    """
    path = method._jlserve_endpoint_path
    input_type = get_method_input_type(method)
    output_type = get_method_output_type(method)
    method_name = method.__name__

    # Create the route handler
    # We need to capture method_name and app_instance in closure
    def create_handler(captured_method_name: str, captured_instance: object):
        def run_locked(input_data):
            endpoint_method = getattr(captured_instance, captured_method_name)
            with call_lock:
                return endpoint_method(input_data)

        async def handler(input_data: input_type) -> output_type:
            """Handle incoming requests by calling the endpoint method."""
            try:
                return await asyncio.to_thread(run_locked, input_data)
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={"detail": str(e)},
                )
        return handler

    # Register the route with FastAPI
    fastapi_app.post(path, response_model=output_type)(create_handler(method_name, app_instance))
