"""Tests for the deploy step functions and the service client, without a network."""

import json
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel

import jlserve
from jlserve.decorator import _reset_registry
from jlserve.deploy import (
    APP_FILE_NAME,
    DEFAULT_ENDPOINT,
    ENDPOINT_ENV,
    FRAMEWORK,
    TOKEN_ENV,
    DeployError,
    ServerlessClient,
    build_create_payload,
    endpoint_urls,
    resolve_endpoint,
    resolve_token,
    wait_until_running,
)


class In(BaseModel):
    x: int


class Out(BaseModel):
    y: int


@pytest.fixture(autouse=True)
def clean_registry():
    _reset_registry()
    yield
    _reset_registry()


def make_app(**kwargs):
    @jlserve.app(**kwargs)
    class Model:
        @jlserve.endpoint()
        def predict(self, input: In) -> Out:
            return Out(y=input.x)

        @jlserve.endpoint(path="/alt")
        def other(self, input: In) -> Out:
            return Out(y=input.x)

    return Model


class TestBuildCreatePayload:
    def test_uses_decorator_settings(self):
        cls = make_app(
            requirements=["diffusers", "torch"],
            gpu="L4", gpus_per_worker=2, min_workers=1, max_workers=3, idle_timeout=120,
        )
        p = build_create_payload(cls)
        assert p["name"] == "Model"
        assert p["framework"] == FRAMEWORK
        assert p["gpus_to_use"] == {"gpus": ["L4"]}
        assert p["gpus_per_worker"] == 2
        assert (p["min_workers"], p["max_workers"], p["idle_timeout"]) == (1, 3, 120)
        assert p["concurrent_requests"] == 1
        assert p["args"] == {"entrypoint": APP_FILE_NAME, "requirements": ["diffusers", "torch"],
                             "weights": []}
        assert p["env"] == {}

    def test_weights_travel_in_args(self):
        cls = make_app(gpu="L4", weights=["stabilityai/sd-turbo"])
        assert build_create_payload(cls)["args"]["weights"] == ["stabilityai/sd-turbo"]

    def test_gpu_override_wins(self):
        cls = make_app(gpu="L4")
        assert build_create_payload(cls, gpu="H100")["gpus_to_use"] == {"gpus": ["H100"]}

    def test_gpu_required(self):
        cls = make_app()
        with pytest.raises(DeployError, match="No GPU type"):
            build_create_payload(cls)

    def test_name_override_and_hf_token(self):
        cls = make_app(gpu="L4")
        p = build_create_payload(cls, name="my-dep", hf_token="hf_abc")
        assert p["name"] == "my-dep"
        assert p["env"] == {"HF_TOKEN": "hf_abc"}

    def test_matches_service_schema_fields(self):
        """Every field the service's DeploymentModel requires is present."""
        p = build_create_payload(make_app(gpu="L4"))
        required = {"name", "min_workers", "max_workers", "wait_time", "framework",
                    "gpus_to_use", "gpus_per_worker", "concurrent_requests",
                    "idle_timeout", "args", "storage"}
        assert required <= set(p)
        assert 0 <= p["wait_time"] <= 600
        assert 50 <= p["storage"] <= 1000


class TestEndpointUrls:
    def test_one_url_per_endpoint_sorted(self):
        cls = make_app(gpu="L4")
        urls = endpoint_urls("https://svc.example/", "01ABC", cls)
        assert urls == (
            "https://svc.example/deployment/01ABC/alt",
            "https://svc.example/deployment/01ABC/predict",
        )


class TestResolve:
    def test_endpoint_default(self, monkeypatch):
        monkeypatch.delenv(ENDPOINT_ENV, raising=False)
        assert resolve_endpoint(None) == DEFAULT_ENDPOINT

    def test_endpoint_env_and_flag(self, monkeypatch):
        monkeypatch.setenv(ENDPOINT_ENV, "https://env.example/")
        assert resolve_endpoint(None) == "https://env.example"
        assert resolve_endpoint("https://flag.example/") == "https://flag.example"

    def test_token_missing(self, monkeypatch):
        monkeypatch.delenv(TOKEN_ENV, raising=False)
        with pytest.raises(DeployError, match=TOKEN_ENV):
            resolve_token(None)

    def test_token_from_env(self, monkeypatch):
        monkeypatch.setenv(TOKEN_ENV, "tok")
        assert resolve_token(None) == "tok"
        assert resolve_token("flag") == "flag"


def fake_service(handler):
    """A client whose HTTP goes to `handler(request) -> Response`."""
    return ServerlessClient("https://svc.example", "secret", transport=httpx.MockTransport(handler))


class TestServerlessClient:
    def test_create_sends_multipart_with_json_and_file(self, tmp_path: Path):
        app_file = tmp_path / "my_app.py"
        app_file.write_text("print('hi')\n")
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["auth"] = request.headers.get("authorization")
            seen["content_type"] = request.headers.get("content-type", "")
            seen["body"] = request.read()
            return httpx.Response(200, json={"deployment_id": "01DEP", "region": "noida"})

        with fake_service(handler) as client:
            result = client.create({"name": "m", "framework": FRAMEWORK}, app_file)

        assert result["deployment_id"] == "01DEP"
        assert seen["url"] == f"https://svc.example/management/{FRAMEWORK}/create"
        assert seen["auth"] == "Bearer secret"
        assert seen["content_type"].startswith("multipart/form-data")
        body = seen["body"]
        assert b'name="deployment"' in body
        assert json.dumps({"name": "m", "framework": FRAMEWORK}).encode() in body
        assert f'filename="{APP_FILE_NAME}"'.encode() in body
        assert b"print('hi')" in body

    def test_status_and_describe_paths(self):
        calls = []

        def handler(request):
            calls.append(request.url.path)
            return httpx.Response(200, json={"status": "running", "error_message": None})

        with fake_service(handler) as client:
            assert client.status("01DEP") == {"status": "running", "error_message": None}
            client.describe("01DEP")
        assert calls == ["/management/01DEP/status", "/management/01DEP"]

    def test_http_error_carries_service_detail(self):
        def handler(request):
            return httpx.Response(400, json={"detail": "GPU types ['B200'] are not available"})

        with fake_service(handler) as client, pytest.raises(DeployError, match="400 GPU types"):
            client.status("01DEP")

    def test_401_is_reported_as_bad_token(self):
        def handler(request):
            return httpx.Response(401, json={"detail": "Invalid token"})

        with fake_service(handler) as client, pytest.raises(DeployError, match="token was rejected"):
            client.status("01DEP")


class FakeClient:
    """Stands in for ServerlessClient in the polling tests."""

    def __init__(self, statuses, error_message=None):
        self.statuses = list(statuses)
        self.error_message = error_message
        self.describe_calls = 0

    def status(self, dep_id):
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return {"status": status}

    def describe(self, dep_id):
        self.describe_calls += 1
        return {"status": "failed", "error_message": self.error_message}


class TestWaitUntilRunning:
    def test_reports_each_state_once_and_returns_running(self):
        client = FakeClient(["starting", "starting", "filesystem_created",
                             "downloading_model", "running"])
        seen = []
        result = wait_until_running(
            client, "01DEP", on_change=lambda s, p: seen.append(s), sleep=lambda _: None,
        )
        assert result == "running"
        assert seen == ["starting", "filesystem_created", "downloading_model", "running"]

    def test_failed_raises_with_service_error(self):
        client = FakeClient(["starting", "failed"], error_message="setup() raised RuntimeError")
        with pytest.raises(DeployError, match="setup\\(\\) raised RuntimeError"):
            wait_until_running(client, "01DEP", sleep=lambda _: None)
        assert client.describe_calls == 1

    def test_deleted_raises(self):
        client = FakeClient(["deleted"])
        with pytest.raises(DeployError, match="deleted"):
            wait_until_running(client, "01DEP", sleep=lambda _: None)

    def test_timeout_raises_with_last_state(self):
        client = FakeClient(["downloading_model"])
        ticks = iter(range(0, 10_000, 100))
        with pytest.raises(DeployError, match="still 'downloading_model' after 300s"):
            wait_until_running(
                client, "01DEP", timeout=300, sleep=lambda _: None, clock=lambda: next(ticks),
            )
