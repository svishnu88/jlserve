"""Unit tests for FastAPI server integration with multi-endpoint apps."""

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

import jlserve
from jlserve.decorator import _reset_registry
from jlserve.exceptions import EndpointSetupError, EndpointValidationError
from jlserve.server import create_app


class Input(BaseModel):
    value: int


class Output(BaseModel):
    result: int


class TwoNumbers(BaseModel):
    a: int
    b: int


class Result(BaseModel):
    result: int


class TestCreateApp:
    """Tests for creating FastAPI apps from Jarvis app classes."""

    def test_creates_fastapi_app(self):
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def process(self, input: Input) -> Output:
                return Output(result=input.value * 2)

        app = create_app(MyApp)
        assert app is not None

    def test_uses_app_name_as_title(self):
        _reset_registry()

        @jlserve.app(name="Calculator")
        class MyApp:
            @jlserve.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

        app = create_app(MyApp)
        assert app.title == "Calculator"

    def test_uses_class_name_as_default_title(self):
        _reset_registry()

        @jlserve.app()
        class MyCalculator:
            @jlserve.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

        app = create_app(MyCalculator)
        assert app.title == "MyCalculator"

    def test_invalid_app_raises_error(self):
        class NotAnApp:
            pass

        with pytest.raises(EndpointValidationError):
            create_app(NotAnApp)


class TestMultiRouteRegistration:
    """Tests for registering multiple endpoint routes."""

    def test_registers_multiple_routes(self):
        _reset_registry()

        @jlserve.app()
        class Calculator:
            @jlserve.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

            @jlserve.endpoint()
            def subtract(self, input: TwoNumbers) -> Result:
                return Result(result=input.a - input.b)

        app = create_app(Calculator)

        # Check routes are registered
        paths = [route.path for route in app.routes if hasattr(route, "path")]
        assert "/add" in paths
        assert "/subtract" in paths

    def test_custom_paths_registered(self):
        _reset_registry()

        @jlserve.app()
        class Calculator:
            @jlserve.endpoint(path="/plus")
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

            @jlserve.endpoint(path="/minus")
            def subtract(self, input: TwoNumbers) -> Result:
                return Result(result=input.a - input.b)

        app = create_app(Calculator)

        paths = [route.path for route in app.routes if hasattr(route, "path")]
        assert "/plus" in paths
        assert "/minus" in paths
        assert "/add" not in paths
        assert "/subtract" not in paths


class TestEndpointRoutes:
    """Tests for endpoint route functionality."""

    def test_post_to_add_endpoint(self):
        _reset_registry()

        @jlserve.app()
        class Calculator:
            @jlserve.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

        app = create_app(Calculator)
        with TestClient(app) as client:
            response = client.post("/add", json={"a": 5, "b": 3})
            assert response.status_code == 200
            assert response.json() == {"result": 8}

    def test_post_to_subtract_endpoint(self):
        _reset_registry()

        @jlserve.app()
        class Calculator:
            @jlserve.endpoint()
            def subtract(self, input: TwoNumbers) -> Result:
                return Result(result=input.a - input.b)

        app = create_app(Calculator)
        with TestClient(app) as client:
            response = client.post("/subtract", json={"a": 10, "b": 4})
            assert response.status_code == 200
            assert response.json() == {"result": 6}

    def test_multiple_endpoints_work_together(self):
        _reset_registry()

        @jlserve.app()
        class Calculator:
            @jlserve.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

            @jlserve.endpoint()
            def subtract(self, input: TwoNumbers) -> Result:
                return Result(result=input.a - input.b)

            @jlserve.endpoint()
            def multiply(self, input: TwoNumbers) -> Result:
                return Result(result=input.a * input.b)

        app = create_app(Calculator)
        with TestClient(app) as client:
            assert client.post("/add", json={"a": 2, "b": 3}).json() == {"result": 5}
            assert client.post("/subtract", json={"a": 5, "b": 2}).json() == {"result": 3}
            assert client.post("/multiply", json={"a": 4, "b": 3}).json() == {"result": 12}

    def test_invalid_input_returns_422(self):
        _reset_registry()

        @jlserve.app()
        class Calculator:
            @jlserve.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

        app = create_app(Calculator)
        with TestClient(app) as client:
            response = client.post("/add", json={"wrong_field": "value"})
            assert response.status_code == 422


class TestSharedState:
    """Tests for shared state across endpoints."""

    def test_shared_instance_across_endpoints(self):
        _reset_registry()

        @jlserve.app()
        class Counter:
            def __init__(self):
                self.count = 0

            @jlserve.endpoint()
            def increment(self, input: Input) -> Output:
                self.count += input.value
                return Output(result=self.count)

            @jlserve.endpoint()
            def get_count(self, input: Input) -> Output:
                return Output(result=self.count)

        app = create_app(Counter)
        with TestClient(app) as client:
            # Increment multiple times
            client.post("/increment", json={"value": 5})
            client.post("/increment", json={"value": 3})

            # Get count should reflect all increments
            response = client.post("/get_count", json={"value": 0})
            assert response.json() == {"result": 8}

    def test_setup_initializes_shared_state(self):
        _reset_registry()

        @jlserve.app()
        class Calculator:
            def setup(self):
                self.multiplier = 10

            @jlserve.endpoint()
            def scale(self, input: Input) -> Output:
                return Output(result=input.value * self.multiplier)

        app = create_app(Calculator)
        with TestClient(app) as client:
            response = client.post("/scale", json={"value": 5})
            assert response.json() == {"result": 50}


class TestSetupMethod:
    """Tests for the setup() method lifecycle."""

    def test_setup_is_called_on_startup(self):
        _reset_registry()

        @jlserve.app()
        class MyApp:
            def setup(self):
                self.prefix = "Processed"

            @jlserve.endpoint()
            def process(self, input: Input) -> Output:
                # If setup wasn't called, this would raise AttributeError
                return Output(result=input.value if self.prefix else 0)

        app = create_app(MyApp)
        with TestClient(app) as client:
            response = client.post("/process", json={"value": 42})
            assert response.status_code == 200

    def test_app_without_setup_works(self):
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def process(self, input: Input) -> Output:
                return Output(result=input.value * 2)

        app = create_app(MyApp)
        with TestClient(app) as client:
            response = client.post("/process", json={"value": 5})
            assert response.status_code == 200
            assert response.json() == {"result": 10}

    def test_setup_failure_prevents_startup(self):
        _reset_registry()

        @jlserve.app()
        class MyApp:
            def setup(self):
                raise RuntimeError("Setup failed!")

            @jlserve.endpoint()
            def process(self, input: Input) -> Output:
                return Output(result=input.value)

        app = create_app(MyApp)
        with pytest.raises(EndpointSetupError) as exc_info:
            with TestClient(app):
                pass
        assert "Setup failed!" in str(exc_info.value)


class TestErrorHandling:
    """Tests for error handling in endpoints."""

    def test_exception_in_endpoint_returns_500(self):
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def failing(self, input: Input) -> Output:
                raise ValueError("Something went wrong")

        app = create_app(MyApp)
        with TestClient(app) as client:
            response = client.post("/failing", json={"value": 1})
            assert response.status_code == 500
            assert "Something went wrong" in response.json()["detail"]


class TestHealthRoute:
    """Tests for GET /health, which the serverless platform polls."""

    def test_health_returns_200_after_setup(self):
        _reset_registry()

        @jlserve.app()
        class MyApp:
            def setup(self):
                self.ready_marker = True

            @jlserve.endpoint()
            def process(self, input: Input) -> Output:
                return Output(result=input.value)

        app = create_app(MyApp)
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    def test_health_returns_503_before_setup(self):
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def process(self, input: Input) -> Output:
                return Output(result=input.value)

        app = create_app(MyApp)
        # No `with` block: the lifespan (and therefore setup) has not run.
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json() == {"status": "starting"}

    def test_health_not_in_openapi_schema(self):
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def process(self, input: Input) -> Output:
                return Output(result=input.value)

        app = create_app(MyApp)
        with TestClient(app) as client:
            paths = client.get("/openapi.json").json()["paths"]
            assert "/health" not in paths
            assert "/process" in paths


class TestThreadedEndpoints:
    """Endpoint methods run in a worker thread, one at a time."""

    def test_health_answers_during_a_slow_endpoint(self):
        import threading
        import time

        _reset_registry()

        started = threading.Event()

        @jlserve.app()
        class SlowApp:
            @jlserve.endpoint()
            def slow(self, input: Input) -> Output:
                started.set()
                time.sleep(1.0)
                return Output(result=input.value)

        app = create_app(SlowApp)
        with TestClient(app) as client:
            results = {}

            def call_slow():
                results["slow"] = client.post("/slow", json={"value": 1})

            t = threading.Thread(target=call_slow)
            t.start()
            assert started.wait(timeout=2.0), "slow endpoint never started"

            t0 = time.monotonic()
            health = client.get("/health")
            elapsed = time.monotonic() - t0
            t.join(timeout=5.0)

            assert health.status_code == 200
            # Must not have waited for the 1s endpoint to finish.
            assert elapsed < 0.5, f"/health blocked for {elapsed:.2f}s"
            assert results["slow"].status_code == 200
            assert results["slow"].json() == {"result": 1}

    def test_endpoint_calls_do_not_overlap(self):
        import threading
        import time

        _reset_registry()

        in_flight = {"count": 0, "max": 0}
        guard = threading.Lock()

        @jlserve.app()
        class Serial:
            @jlserve.endpoint()
            def work(self, input: Input) -> Output:
                with guard:
                    in_flight["count"] += 1
                    in_flight["max"] = max(in_flight["max"], in_flight["count"])
                time.sleep(0.3)
                with guard:
                    in_flight["count"] -= 1
                return Output(result=input.value)

        app = create_app(Serial)
        with TestClient(app) as client:
            threads = [
                threading.Thread(target=lambda: client.post("/work", json={"value": i}))
                for i in range(3)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5.0)

        assert in_flight["max"] == 1, "endpoint calls overlapped"

    def test_exception_in_thread_still_returns_500(self):
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def failing(self, input: Input) -> Output:
                raise ValueError("boom in thread")

        app = create_app(MyApp)
        with TestClient(app) as client:
            response = client.post("/failing", json={"value": 1})
            assert response.status_code == 500
            assert "boom in thread" in response.json()["detail"]


class TestOnReady:
    """The on_ready callback fires only after setup() has succeeded."""

    def test_on_ready_called_after_setup(self):
        _reset_registry()
        events = []

        @jlserve.app()
        class MyApp:
            def setup(self):
                events.append("setup")

            @jlserve.endpoint()
            def process(self, input: Input) -> Output:
                return Output(result=input.value)

        app = create_app(MyApp, on_ready=lambda: events.append("ready"))
        assert events == []
        with TestClient(app):
            assert events == ["setup", "ready"]

    def test_on_ready_not_called_when_setup_fails(self):
        _reset_registry()
        events = []

        @jlserve.app()
        class MyApp:
            def setup(self):
                raise RuntimeError("no model")

            @jlserve.endpoint()
            def process(self, input: Input) -> Output:
                return Output(result=input.value)

        app = create_app(MyApp, on_ready=lambda: events.append("ready"))
        with pytest.raises(EndpointSetupError):
            with TestClient(app):
                pass
        assert events == []


class TestOpenAPIDocs:
    """Tests for OpenAPI documentation."""

    def test_openapi_docs_available(self):
        _reset_registry()

        @jlserve.app(name="Calculator")
        class Calculator:
            @jlserve.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

        app = create_app(Calculator)
        client = TestClient(app)

        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json_has_all_endpoints(self):
        _reset_registry()

        @jlserve.app(name="Calculator")
        class Calculator:
            @jlserve.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

            @jlserve.endpoint()
            def subtract(self, input: TwoNumbers) -> Result:
                return Result(result=input.a - input.b)

        app = create_app(Calculator)
        client = TestClient(app)

        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi = response.json()
        assert openapi["info"]["title"] == "Calculator"
        assert "/add" in openapi["paths"]
        assert "/subtract" in openapi["paths"]
        assert "post" in openapi["paths"]["/add"]
        assert "post" in openapi["paths"]["/subtract"]
