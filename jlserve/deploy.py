"""Deploy an app to JarvisLabs serverless.

The deploy command has four steps, each a function here so they can be tested
without a network:

1. ``build_create_payload``: turn the decorated class into the create request
   the serverless service expects. Every field except ``framework``, ``args``
   and ``concurrent_requests`` is the same one a vllm deployment sends.
2. ``ServerlessClient.create``: one multipart call carrying that JSON and the
   app file. The service writes the file into the deployment's filesystem and
   the worker finds it at ``/model_weights/jlserve/app.py``.
3. ``wait_until_running``: poll the status route until the deployment is
   running or failed.
4. ``endpoint_urls``: the public URLs, one per endpoint method.

Service contract used here (the ``jlserve`` framework is new on the service):

    POST {endpoint}/management/jlserve/create      multipart: deployment=<json>, file=<app.py>
        -> {"deployment_id": ..., "region": ...}
    GET  {endpoint}/management/{dep_id}/status      -> {"status": ...}
    GET  {endpoint}/management/{dep_id}             -> full record, error_message when failed
    POST {endpoint}/deployment/{dep_id}{path}       -> the customer's endpoint, body {"input": ...}
"""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Type

import httpx

from jlserve.decorator import get_deploy_settings, get_endpoint_methods

DEFAULT_ENDPOINT = "https://serverlessn.jarvislabs.net"
ENDPOINT_ENV = "JLSERVE_ENDPOINT"
TOKEN_ENV = "JARVISLABS_API_TOKEN"

FRAMEWORK = "jlserve"
APP_FILE_NAME = "app.py"          # what the file is called on the deployment filesystem
STORAGE_GB = 50                   # service minimum; for serverless it only affects price
WAIT_TIME_SECONDS = 600           # service maximum: how long a request waits for a worker
CONCURRENT_REQUESTS = 1           # one request per worker; the SDK serialises anyway

POLL_SECONDS = 3.0
DEFAULT_TIMEOUT_SECONDS = 900.0
TERMINAL_STATES = frozenset({"running", "failed", "deleted"})


class DeployError(Exception):
    """A deploy step failed with a message fit to show the user."""


@dataclass(frozen=True)
class DeployResult:
    deployment_id: str
    region: str
    status: str
    urls: tuple[str, ...]


def build_create_payload(
    app_cls: Type,
    *,
    name: Optional[str] = None,
    gpu: Optional[str] = None,
    hf_token: Optional[str] = None,
) -> dict:
    """Build the create request body from a decorated app class.

    Args:
        app_cls: A class decorated with @jlserve.app().
        name: Deployment name. Defaults to the app name.
        gpu: GPU type. Overrides the decorator; required if the decorator has none.
        hf_token: Hugging Face token forwarded to the worker as HF_TOKEN.

    Raises:
        DeployError: If no GPU type is known.
    """
    settings = get_deploy_settings(app_cls)
    gpu_type = gpu or settings.gpu
    if not gpu_type:
        raise DeployError(
            "No GPU type given. Set gpu=... on @jlserve.app() or pass --gpu, e.g. --gpu L4"
        )

    env: dict[str, str] = {}
    if hf_token:
        env["HF_TOKEN"] = hf_token

    return {
        "name": name or app_cls._jlserve_app_name,
        "framework": FRAMEWORK,
        "gpus_to_use": {"gpus": [gpu_type]},
        "gpus_per_worker": settings.gpus_per_worker,
        "min_workers": settings.min_workers,
        "max_workers": settings.max_workers,
        "idle_timeout": settings.idle_timeout,
        "concurrent_requests": CONCURRENT_REQUESTS,
        "wait_time": WAIT_TIME_SECONDS,
        "storage": STORAGE_GB,
        "args": {
            "entrypoint": APP_FILE_NAME,
            "requirements": list(app_cls._jlserve_requirements),
        },
        "env": env,
    }


def endpoint_urls(endpoint: str, deployment_id: str, app_cls: Type) -> tuple[str, ...]:
    """Public URL for each endpoint method, in a stable order."""
    base = endpoint.rstrip("/")
    paths = sorted(m._jlserve_endpoint_path for m in get_endpoint_methods(app_cls))
    return tuple(f"{base}/deployment/{deployment_id}{path}" for path in paths)


def resolve_endpoint(value: Optional[str]) -> str:
    return (value or os.environ.get(ENDPOINT_ENV) or DEFAULT_ENDPOINT).rstrip("/")


def resolve_token(value: Optional[str]) -> str:
    token = value or os.environ.get(TOKEN_ENV)
    if not token:
        raise DeployError(
            f"No API token. Pass --token or set {TOKEN_ENV}. "
            "The token is the one from your JarvisLabs account settings."
        )
    return token


class ServerlessClient:
    """Thin client for the serverless management routes."""

    def __init__(
        self,
        endpoint: str,
        token: str,
        *,
        timeout: float = 60.0,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self.endpoint = endpoint.rstrip("/")
        self._client = httpx.Client(
            base_url=self.endpoint,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ServerlessClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def create(self, payload: dict, app_file: Path) -> dict:
        """Create the deployment and upload the app file in one call."""
        with app_file.open("rb") as fh:
            response = self._client.post(
                f"/management/{FRAMEWORK}/create",
                data={"deployment": json.dumps(payload)},
                files={"file": (APP_FILE_NAME, fh, "text/x-python")},
            )
        return self._json(response, "create deployment")

    def status(self, deployment_id: str) -> dict:
        return self._json(self._client.get(f"/management/{deployment_id}/status"), "get status")

    def describe(self, deployment_id: str) -> dict:
        return self._json(self._client.get(f"/management/{deployment_id}"), "get deployment")

    @staticmethod
    def _json(response: httpx.Response, action: str) -> dict:
        if response.is_success:
            return response.json()
        detail: object
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        if response.status_code in (401, 403):
            raise DeployError(f"Could not {action}: the API token was rejected ({response.status_code})")
        raise DeployError(f"Could not {action}: {response.status_code} {detail}")


def wait_until_running(
    client: ServerlessClient,
    deployment_id: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    poll_seconds: float = POLL_SECONDS,
    on_change: Optional[Callable[[str, dict], None]] = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> str:
    """Poll until the deployment reaches a terminal state.

    Returns the final status. Raises DeployError on ``failed`` (with the
    service's error message), on ``deleted``, or on timeout.
    """
    deadline = clock() + timeout
    last: Optional[str] = None
    while True:
        payload = client.status(deployment_id)
        status = payload.get("status", "unknown")
        if status != last:
            if on_change:
                on_change(status, payload)
            last = status
        if status == "running":
            return status
        if status == "failed":
            record = client.describe(deployment_id)
            message = record.get("error_message") or "no error message recorded"
            raise DeployError(f"Deployment {deployment_id} failed: {message}")
        if status == "deleted":
            raise DeployError(f"Deployment {deployment_id} was deleted before it started")
        if clock() >= deadline:
            raise DeployError(
                f"Deployment {deployment_id} is still '{status}' after {int(timeout)}s. "
                f"It may still come up; check its status with the JarvisLabs dashboard."
            )
        sleep(poll_seconds)
