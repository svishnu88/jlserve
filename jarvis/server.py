"""FastAPI server integration for Jarvis apps."""

from contextlib import asynccontextmanager
from typing import Callable, Type

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from jarvis.decorator import get_endpoint_methods
from jarvis.exceptions import EndpointSetupError
from jarvis.validator import get_method_input_type, get_method_output_type, validate_app


def create_app(app_cls: Type) -> FastAPI:
    """Create a FastAPI app from a Jarvis app class.

    Args:
        app_cls: The app class decorated with @jarvis.app().

    Returns:
        A configured FastAPI application with routes for all endpoints.

    Raises:
        EndpointValidationError: If the app class is invalid.
        EndpointSetupError: If the setup() method fails.
    """
    validate_app(app_cls)

    app_name = getattr(app_cls, "_jarvis_app_name", "app")
    endpoint_methods = get_endpoint_methods(app_cls)

    # Create the app instance once - shared across all endpoints
    app_instance = app_cls()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Call setup() if it exists
        if hasattr(app_instance, "setup") and callable(app_instance.setup):
            try:
                app_instance.setup()
            except Exception as e:
                raise EndpointSetupError(f"setup() failed: {e}") from e

        yield

    fastapi_app = FastAPI(title=app_name, lifespan=lifespan)

    # Register a POST route for each endpoint method
    for method in endpoint_methods:
        _register_endpoint_route(fastapi_app, method, app_instance)

    return fastapi_app


def _register_endpoint_route(fastapi_app: FastAPI, method: Callable, app_instance: object) -> None:
    """Register a POST route for an endpoint method.

    Args:
        fastapi_app: The FastAPI application to register the route on.
        method: The endpoint method to create a route for.
        app_instance: The shared app instance to call methods on.
    """
    path = method._jarvis_endpoint_path
    input_type = get_method_input_type(method)
    output_type = get_method_output_type(method)
    method_name = method.__name__

    # Create the route handler
    # We need to capture method_name and app_instance in closure
    def create_handler(captured_method_name: str, captured_instance: object):
        async def handler(input_data: input_type) -> output_type:
            """Handle incoming requests by calling the endpoint method."""
            endpoint_method = getattr(captured_instance, captured_method_name)
            try:
                return endpoint_method(input_data)
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={"detail": str(e)},
                )
        return handler

    # Register the route with FastAPI
    fastapi_app.post(path, response_model=output_type)(create_handler(method_name, app_instance))
