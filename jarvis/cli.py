"""CLI implementation for Jarvis SDK."""

import importlib.util
import sys
from pathlib import Path
from typing import Optional

import typer
import uvicorn

from jarvis.decorator import get_registered_endpoints, clear_registry
from jarvis.server import create_app

app = typer.Typer(
    help="Jarvis SDK - A simple framework for creating ML endpoints",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def callback() -> None:
    """Jarvis SDK - A simple framework for creating ML endpoints."""
    pass


@app.command("dev")
def dev(
    file: Path = typer.Argument(..., help="Path to the Python file containing the endpoint"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to serve on"),
) -> None:
    """Run an endpoint locally for development."""
    if not file.exists():
        typer.echo(f"Error: File not found: {file}", err=True)
        raise typer.Exit(1)

    if not file.suffix == ".py":
        typer.echo(f"Error: File must be a Python file: {file}", err=True)
        raise typer.Exit(1)

    # Clear any previously registered endpoints
    clear_registry()

    # Load the user's Python file
    spec = importlib.util.spec_from_file_location("user_module", file)
    if spec is None or spec.loader is None:
        typer.echo(f"Error: Could not load file: {file}", err=True)
        raise typer.Exit(1)

    module = importlib.util.module_from_spec(spec)
    sys.modules["user_module"] = module
    spec.loader.exec_module(module)

    # Get registered endpoints
    endpoints = get_registered_endpoints()
    if not endpoints:
        typer.echo("Error: No endpoints found. Did you decorate a class with @jarvis.endpoint()?", err=True)
        raise typer.Exit(1)

    if len(endpoints) > 1:
        typer.echo(f"Warning: Multiple endpoints found. Using the first one.", err=True)

    endpoint_cls = endpoints[0]
    endpoint_name = getattr(endpoint_cls, "_jarvis_endpoint_name", "endpoint")

    # Create the FastAPI app
    fastapi_app = create_app(endpoint_cls)

    # Print startup message
    typer.echo(f"Serving {endpoint_name} at http://localhost:{port}")
    typer.echo(f"Docs at http://localhost:{port}/docs")

    # Start Uvicorn server
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    app()
