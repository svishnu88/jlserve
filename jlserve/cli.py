"""CLI implementation for JLServe."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Optional, Type

import httpx
import typer
import uvicorn

from jlserve.decorator import (
    _reset_registry,
    get_deploy_settings,
    get_endpoint_methods,
    get_registered_app,
)
from jlserve.deploy import (
    DEFAULT_TIMEOUT_SECONDS,
    ENDPOINT_ENV,
    TOKEN_ENV,
    DeployError,
    ServerlessClient,
    build_create_payload,
    endpoint_urls,
    resolve_endpoint,
    resolve_token,
    wait_until_running,
)
from jlserve.exceptions import EndpointValidationError
from jlserve.requirements import extract_requirements_from_file
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


def _check_file(file: Path) -> None:
    if not file.exists():
        typer.echo(f"Error: File not found: {file}", err=True)
        raise typer.Exit(1)
    if not file.suffix == ".py":
        typer.echo(f"Error: File must be a Python file: {file}", err=True)
        raise typer.Exit(1)


def _load_app_class(file: Path) -> Type:
    """Import the user's file and return the class it registered with @jlserve.app().

    Exits with a one-line message when the file registers no app, registers two,
    or has no endpoint methods. Other import errors propagate with their traceback,
    since they are bugs in the user's file.
    """
    _reset_registry()

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

    app_cls = get_registered_app()
    if app_cls is None:
        typer.echo(
            "Error: No app found. Did you decorate a class with @jlserve.app()?",
            err=True,
        )
        raise typer.Exit(1)

    app_name = getattr(app_cls, "_jlserve_app_name", "app")
    if not get_endpoint_methods(app_cls):
        typer.echo(
            f"Error: App {app_name} has no endpoints. Add methods decorated with @jlserve.endpoint().",
            err=True,
        )
        raise typer.Exit(1)

    return app_cls


def _validate_or_exit(app_cls: Type) -> None:
    """Run the structural validation, printing only the message on failure."""
    try:
        validate_app(app_cls)
    except EndpointValidationError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("dev")
def dev(
    file: Path = typer.Argument(..., help="Path to the Python file containing the app"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to serve on"),
) -> None:
    """Run an app locally for development."""
    _check_file(file)

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

    app_cls = _load_app_class(file)
    _validate_or_exit(app_cls)
    app_name = getattr(app_cls, "_jlserve_app_name", "app")
    endpoint_methods = get_endpoint_methods(app_cls)

    # Print the banner only once setup() has finished, so "Serving" is never
    # shown for a server that cannot serve yet (a model may take minutes to load).
    def print_ready_banner() -> None:
        typer.echo(f"\nServing {app_name} at http://localhost:{port}")
        typer.echo(f"Docs at http://localhost:{port}/docs")
        typer.echo(f"Health at http://localhost:{port}/health\n")
        routes = [f"POST {m._jlserve_endpoint_path}" for m in endpoint_methods]
        typer.echo(f"Endpoints: {', '.join(routes)}\n")

    # Create the FastAPI app
    fastapi_app = create_app(app_cls, on_ready=print_ready_banner)

    typer.echo(f"Starting {app_name}: running setup() ...")

    # Start Uvicorn server
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port, log_level="info")


@app.command("deploy")
def deploy(
    file: Path = typer.Argument(..., help="Path to the Python file containing the app"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Deployment name. Defaults to the app name."),
    gpu: Optional[str] = typer.Option(None, "--gpu", help="GPU type, e.g. L4 or H100. Overrides gpu= on the decorator."),
    token: Optional[str] = typer.Option(None, "--token", envvar=TOKEN_ENV, help="JarvisLabs API token."),
    endpoint: Optional[str] = typer.Option(None, "--endpoint", envvar=ENDPOINT_ENV, help="Serverless service URL for the region."),
    hf_token: Optional[str] = typer.Option(None, "--hf-token", envvar="HF_TOKEN", help="Hugging Face token, for gated models."),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait until the deployment is running."),
    timeout: float = typer.Option(DEFAULT_TIMEOUT_SECONDS, "--timeout", help="Seconds to wait for running."),
) -> None:
    """Deploy an app to JarvisLabs serverless.

    Validates the file locally, sends it with the deploy settings from
    @jlserve.app(), and prints the endpoint URLs once the deployment is running.
    """
    _check_file(file)

    typer.echo(f"Validating {file} ...")
    app_cls = _load_app_class(file)
    _validate_or_exit(app_cls)

    try:
        endpoint_url = resolve_endpoint(endpoint)
        api_token = resolve_token(token)
        payload = build_create_payload(app_cls, name=name, gpu=gpu, hf_token=hf_token)
    except DeployError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    settings = get_deploy_settings(app_cls)
    routes = ", ".join(f"POST {m._jlserve_endpoint_path}" for m in get_endpoint_methods(app_cls))
    typer.echo(f"App: {payload['name']}  Endpoints: {routes}")
    typer.echo(
        f"GPU: {payload['gpus_to_use']['gpus'][0]} x{settings.gpus_per_worker}  "
        f"Workers: {settings.min_workers}-{settings.max_workers}  "
        f"Idle timeout: {settings.idle_timeout}s"
    )
    if payload["args"]["requirements"]:
        typer.echo(f"Requirements: {', '.join(payload['args']['requirements'])}")
    if payload["args"]["weights"]:
        typer.echo(f"Weights (downloaded before the worker starts): {', '.join(payload['args']['weights'])}")
    else:
        typer.echo(
            "Weights: none declared. Workers have no internet; if setup() loads a "
            "Hub model, add weights=[...] to @jlserve.app()."
        )

    try:
        with ServerlessClient(endpoint_url, api_token) as client:
            typer.echo(f"Creating deployment at {endpoint_url} ...")
            created = client.create(payload, file)
            dep_id = created["deployment_id"]
            typer.echo(f"Deployment id: {dep_id}")

            urls = endpoint_urls(endpoint_url, dep_id, app_cls)
            if not wait:
                typer.echo("Not waiting. Endpoints once running:")
                for url in urls:
                    typer.echo(f"  {url}")
                return

            def on_change(status: str, _payload: dict) -> None:
                typer.echo(f"  status: {status}")

            wait_until_running(client, dep_id, timeout=timeout, on_change=on_change)
    except DeployError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        typer.echo(f"Error: Could not reach {endpoint_url}: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\nDeployment {dep_id} is running.\n")
    typer.echo("Endpoints:")
    for url in urls:
        typer.echo(f"  {url}")
    typer.echo(
        "\nCall one with your API token; the body goes under \"input\", "
        "and the response carries a request id to poll:\n"
    )
    typer.echo(f"  curl -X POST {urls[0]} \\")
    typer.echo('    -H "Authorization: Bearer $' + TOKEN_ENV + '" \\')
    typer.echo('    -H "Content-Type: application/json" \\')
    typer.echo("    -d '{\"input\": {...}}'")


if __name__ == "__main__":
    app()
