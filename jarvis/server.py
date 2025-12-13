"""FastAPI server integration for Jarvis endpoints."""

from contextlib import asynccontextmanager
from typing import Type

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from jarvis.exceptions import EndpointSetupError
from jarvis.validator import get_input_type, get_output_type, validate_endpoint


def create_app(endpoint_cls: Type) -> FastAPI:
    """Create a FastAPI app from an endpoint class.

    Args:
        endpoint_cls: The endpoint class decorated with @jarvis.endpoint().

    Returns:
        A configured FastAPI application.

    Raises:
        EndpointValidationError: If the endpoint class is invalid.
        EndpointSetupError: If the setup() method fails.
    """
    validate_endpoint(endpoint_cls)

    endpoint_name = getattr(endpoint_cls, "_jarvis_endpoint_name", "endpoint")
    input_type = get_input_type(endpoint_cls)
    output_type = get_output_type(endpoint_cls)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Instantiate the endpoint class
        endpoint_instance = endpoint_cls()

        # Call setup() if it exists
        if hasattr(endpoint_instance, "setup") and callable(endpoint_instance.setup):
            try:
                endpoint_instance.setup()
            except Exception as e:
                raise EndpointSetupError(f"setup() failed: {e}") from e

        # Store instance in app state for access in routes
        app.state.endpoint_instance = endpoint_instance

        yield

    app = FastAPI(title=endpoint_name, lifespan=lifespan)

    @app.post("/", response_model=output_type)
    async def run_endpoint(request: Request, input_data: input_type) -> output_type:
        """Handle incoming requests by calling the endpoint's run() method."""
        instance = request.app.state.endpoint_instance
        try:
            return instance.run(input_data)
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"detail": str(e)},
            )

    return app
