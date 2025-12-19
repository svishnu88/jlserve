"""Unit tests for FastAPI server integration with multi-endpoint apps."""

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

import jarvis
from jarvis.decorator import _reset_registry
from jarvis.exceptions import EndpointSetupError, EndpointValidationError
from jarvis.server import create_app


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

        @jarvis.app()
        class MyApp:
            @jarvis.endpoint()
            def process(self, input: Input) -> Output:
                return Output(result=input.value * 2)

        app = create_app(MyApp)
        assert app is not None

    def test_uses_app_name_as_title(self):
        _reset_registry()

        @jarvis.app(name="Calculator")
        class MyApp:
            @jarvis.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

        app = create_app(MyApp)
        assert app.title == "Calculator"

    def test_uses_class_name_as_default_title(self):
        _reset_registry()

        @jarvis.app()
        class MyCalculator:
            @jarvis.endpoint()
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

        @jarvis.app()
        class Calculator:
            @jarvis.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

            @jarvis.endpoint()
            def subtract(self, input: TwoNumbers) -> Result:
                return Result(result=input.a - input.b)

        app = create_app(Calculator)

        # Check routes are registered
        paths = [route.path for route in app.routes if hasattr(route, "path")]
        assert "/add" in paths
        assert "/subtract" in paths

    def test_custom_paths_registered(self):
        _reset_registry()

        @jarvis.app()
        class Calculator:
            @jarvis.endpoint(path="/plus")
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

            @jarvis.endpoint(path="/minus")
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

        @jarvis.app()
        class Calculator:
            @jarvis.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

        app = create_app(Calculator)
        with TestClient(app) as client:
            response = client.post("/add", json={"a": 5, "b": 3})
            assert response.status_code == 200
            assert response.json() == {"result": 8}

    def test_post_to_subtract_endpoint(self):
        _reset_registry()

        @jarvis.app()
        class Calculator:
            @jarvis.endpoint()
            def subtract(self, input: TwoNumbers) -> Result:
                return Result(result=input.a - input.b)

        app = create_app(Calculator)
        with TestClient(app) as client:
            response = client.post("/subtract", json={"a": 10, "b": 4})
            assert response.status_code == 200
            assert response.json() == {"result": 6}

    def test_multiple_endpoints_work_together(self):
        _reset_registry()

        @jarvis.app()
        class Calculator:
            @jarvis.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

            @jarvis.endpoint()
            def subtract(self, input: TwoNumbers) -> Result:
                return Result(result=input.a - input.b)

            @jarvis.endpoint()
            def multiply(self, input: TwoNumbers) -> Result:
                return Result(result=input.a * input.b)

        app = create_app(Calculator)
        with TestClient(app) as client:
            assert client.post("/add", json={"a": 2, "b": 3}).json() == {"result": 5}
            assert client.post("/subtract", json={"a": 5, "b": 2}).json() == {"result": 3}
            assert client.post("/multiply", json={"a": 4, "b": 3}).json() == {"result": 12}

    def test_invalid_input_returns_422(self):
        _reset_registry()

        @jarvis.app()
        class Calculator:
            @jarvis.endpoint()
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

        @jarvis.app()
        class Counter:
            def __init__(self):
                self.count = 0

            @jarvis.endpoint()
            def increment(self, input: Input) -> Output:
                self.count += input.value
                return Output(result=self.count)

            @jarvis.endpoint()
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

        @jarvis.app()
        class Calculator:
            def setup(self):
                self.multiplier = 10

            @jarvis.endpoint()
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

        @jarvis.app()
        class MyApp:
            def setup(self):
                self.prefix = "Processed"

            @jarvis.endpoint()
            def process(self, input: Input) -> Output:
                # If setup wasn't called, this would raise AttributeError
                return Output(result=input.value if self.prefix else 0)

        app = create_app(MyApp)
        with TestClient(app) as client:
            response = client.post("/process", json={"value": 42})
            assert response.status_code == 200

    def test_app_without_setup_works(self):
        _reset_registry()

        @jarvis.app()
        class MyApp:
            @jarvis.endpoint()
            def process(self, input: Input) -> Output:
                return Output(result=input.value * 2)

        app = create_app(MyApp)
        with TestClient(app) as client:
            response = client.post("/process", json={"value": 5})
            assert response.status_code == 200
            assert response.json() == {"result": 10}

    def test_setup_failure_prevents_startup(self):
        _reset_registry()

        @jarvis.app()
        class MyApp:
            def setup(self):
                raise RuntimeError("Setup failed!")

            @jarvis.endpoint()
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

        @jarvis.app()
        class MyApp:
            @jarvis.endpoint()
            def failing(self, input: Input) -> Output:
                raise ValueError("Something went wrong")

        app = create_app(MyApp)
        with TestClient(app) as client:
            response = client.post("/failing", json={"value": 1})
            assert response.status_code == 500
            assert "Something went wrong" in response.json()["detail"]


class TestOpenAPIDocs:
    """Tests for OpenAPI documentation."""

    def test_openapi_docs_available(self):
        _reset_registry()

        @jarvis.app(name="Calculator")
        class Calculator:
            @jarvis.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

        app = create_app(Calculator)
        client = TestClient(app)

        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json_has_all_endpoints(self):
        _reset_registry()

        @jarvis.app(name="Calculator")
        class Calculator:
            @jarvis.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                return Result(result=input.a + input.b)

            @jarvis.endpoint()
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
