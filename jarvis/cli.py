"""CLI implementation for Jarvis SDK."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import typer
import uvicorn

from jarvis.decorator import _reset_registry, get_endpoint_methods, get_registered_app
from jarvis.requirements import extract_requirements_from_file
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
    file: Path = typer.Argument(..., help="Path to the Python file containing the app"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to serve on"),
) -> None:
    """Run an app locally for development."""
    if not file.exists():
        typer.echo(f"Error: File not found: {file}", err=True)
        raise typer.Exit(1)

    if not file.suffix == ".py":
        typer.echo(f"Error: File must be a Python file: {file}", err=True)
        raise typer.Exit(1)

    # Step 1: Extract requirements via AST (before importing to avoid import errors)
    try:
        requirements = extract_requirements_from_file(str(file))
    except SyntaxError as e:
        typer.echo(f"Error: Invalid Python syntax in {file}: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: Failed to extract requirements from {file}: {e}", err=True)
        raise typer.Exit(1)

    # Step 2: Install requirements with uv (shows output, fast if already satisfied)
    if requirements:
        typer.echo(f"Installing requirements: {', '.join(requirements)}")
        try:
            subprocess.run(
                ["uv", "pip", "install", *requirements],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            typer.echo(f"Error: Failed to install requirements: {e}", err=True)
            raise typer.Exit(1)
        except FileNotFoundError:
            typer.echo(
                "Error: 'uv' command not found. Please install uv: https://github.com/astral-sh/uv",
                err=True,
            )
            raise typer.Exit(1)

    # Clear any previously registered app
    _reset_registry()

    # Load the user's Python file
    spec = importlib.util.spec_from_file_location("user_module", file)
    if spec is None or spec.loader is None:
        typer.echo(f"Error: Could not load file: {file}", err=True)
        raise typer.Exit(1)

    module = importlib.util.module_from_spec(spec)
    sys.modules["user_module"] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        # Check if it's a MultipleAppsError
        if "MultipleAppsError" in type(e).__name__ or "multiple" in str(e).lower():
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
        # Re-raise other exceptions
        raise

    # Get the registered app
    app_cls = get_registered_app()
    if app_cls is None:
        typer.echo(
            "Error: No app found. Did you decorate a class with @jarvis.app()?",
            err=True,
        )
        raise typer.Exit(1)

    app_name = getattr(app_cls, "_jarvis_app_name", "app")

    # Get endpoint methods for display
    endpoint_methods = get_endpoint_methods(app_cls)
    if not endpoint_methods:
        typer.echo(
            f"Error: App {app_name} has no endpoints. Add methods decorated with @jarvis.endpoint().",
            err=True,
        )
        raise typer.Exit(1)

    # Create the FastAPI app
    fastapi_app = create_app(app_cls)

    # Print startup message
    typer.echo(f"\nServing {app_name} at http://localhost:{port}")
    typer.echo(f"Docs at http://localhost:{port}/docs\n")

    # Print all available endpoints
    routes = [f"POST {m._jarvis_endpoint_path}" for m in endpoint_methods]
    typer.echo(f"Endpoints: {', '.join(routes)}\n")

    # Start Uvicorn server
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    app()
