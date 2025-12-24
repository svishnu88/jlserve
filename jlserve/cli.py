"""CLI implementation for JLServe."""

from pathlib import Path

import typer
import uvicorn

from jlserve.cli_utils import install_requirements, load_app_class, validate_python_file
from jlserve.config import get_jlserve_cache_dir
from jlserve.decorator import get_endpoint_methods
from jlserve.exceptions import CacheConfigError
from jlserve.server import create_app
from jlserve.validator import validate_app

app = typer.Typer(
    help="JLServe - A simple framework for creating ML endpoints",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def callback() -> None:
    """JLServe - A simple framework for creating ML endpoints."""
    pass


@app.command("dev")
def dev(
    file: Path = typer.Argument(..., help="Path to the Python file containing the app"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to serve on"),
) -> None:
    """Run an app locally for development."""
    # Validate file exists and is a Python file
    validate_python_file(file)

    # Check that build was run (marker file exists in cache)
    try:
        cache_dir = get_jlserve_cache_dir()
    except CacheConfigError as e:
        typer.echo(f"Error: {e}", err=True)
        typer.echo(
            "\nPlease set JLSERVE_CACHE_DIR and run 'jlserve build' first:",
            err=True,
        )
        typer.echo(f"  export JLSERVE_CACHE_DIR=/path/to/cache", err=True)
        typer.echo(f"  jlserve build {file}", err=True)
        raise typer.Exit(1)

    marker_file = cache_dir / ".jlserve-build-complete"
    if not marker_file.exists():
        typer.echo(
            f"Error: Build marker not found in {cache_dir}",
            err=True,
        )
        typer.echo(
            "\nThis suggests 'jlserve build' has not been run yet.",
            err=True,
        )
        typer.echo("\nPlease run:", err=True)
        typer.echo(f"  jlserve build {file}", err=True)
        typer.echo("\nThen try again:", err=True)
        typer.echo(f"  jlserve dev {file} --port {port}", err=True)
        raise typer.Exit(1)

    # Extract and install any requirements specified in @jlserve.app(requirements=[...])
    # This happens before import to avoid chicken-and-egg problems
    install_requirements(file, cache_dir)

    # Import the file and get the @jlserve.app() decorated class
    app_cls = load_app_class(file)

    # Get the app name for display purposes
    app_name = getattr(app_cls, "_jlserve_app_name", "app")

    # Get endpoint methods for display
    endpoint_methods = get_endpoint_methods(app_cls)
    if not endpoint_methods:
        typer.echo(
            f"Error: App {app_name} has no endpoints. Add methods decorated with @jlserve.endpoint().",
            err=True,
        )
        raise typer.Exit(1)

    # Create the FastAPI app
    fastapi_app = create_app(app_cls)

    # Print startup message
    typer.echo(f"\nServing {app_name} at http://localhost:{port}")
    typer.echo(f"Docs at http://localhost:{port}/docs\n")

    # Print all available endpoints
    routes = [f"POST {m._jlserve_endpoint_path}" for m in endpoint_methods]
    typer.echo(f"Endpoints: {', '.join(routes)}\n")

    # Start Uvicorn server
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port, log_level="info")


@app.command("build")
def build(
    file: Path = typer.Argument(..., help="Path to the Python file containing the app"),
) -> None:
    """Build app by installing dependencies and downloading weights to cache.

    This command is used in deployment pipelines to:
    1. Install all required dependencies
    2. Pre-download model weights to the cache directory
    3. Validate the app structure before deployment
    """
    # Validate file exists and is a Python file
    validate_python_file(file)

    # Check that JLSERVE_CACHE_DIR is configured (required for build)
    try:
        cache_dir = get_jlserve_cache_dir()
        typer.echo(f"✓ Cache directory: {cache_dir}")
    except CacheConfigError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    # Extract and install requirements via AST parsing (before import)
    install_requirements(file, cache_dir)

    # Import the file and get the @jlserve.app() decorated class
    app_cls = load_app_class(file)
    app_name = getattr(app_cls, "_jlserve_app_name", "app")

    # Validate app has required lifecycle methods (setup, download_weights, endpoints)
    try:
        validate_app(app_cls)
    except Exception as e:
        typer.echo(f"Error: App validation failed: {e}", err=True)
        raise typer.Exit(1)

    # Create app instance and trigger weight download
    typer.echo(f"✓ Loading app: {app_name}")
    app_instance = app_cls()

    # Call download_weights() to pre-fetch model files to cache
    typer.echo("✓ Downloading weights...")
    try:
        app_instance.download_weights()
    except Exception as e:
        typer.echo(f"Error: download_weights() failed: {e}", err=True)
        raise typer.Exit(1)

    # Create marker file to indicate build completed successfully
    marker_file = cache_dir / ".jlserve-build-complete"
    marker_file.touch()
    typer.echo("✓ Build complete!")


if __name__ == "__main__":
    app()
