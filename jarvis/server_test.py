"""Unit tests for FastAPI server integration."""

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from jarvis.exceptions import EndpointValidationError
from jarvis.server import create_app


class Input(BaseModel):
    name: str


class Output(BaseModel):
    message: str


class TestCreateApp:
    def test_creates_fastapi_app(self):
        class MyEndpoint:
            def run(self, input: Input) -> Output:
                return Output(message=f"Hello, {input.name}!")

        app = create_app(MyEndpoint)
        assert app is not None
        assert app.title == "endpoint"  # No _jarvis_endpoint_name set

    def test_uses_endpoint_name_as_title(self):
        class MyEndpoint:
            _jarvis_endpoint_name = "greeter"

            def run(self, input: Input) -> Output:
                return Output(message=f"Hello, {input.name}!")

        app = create_app(MyEndpoint)
        assert app.title == "greeter"

    def test_invalid_endpoint_raises_error(self):
        class InvalidEndpoint:
            pass

        with pytest.raises(EndpointValidationError):
            create_app(InvalidEndpoint)


class TestEndpointRoute:
    def test_post_returns_valid_response(self):
        class MyEndpoint:
            def run(self, input: Input) -> Output:
                return Output(message=f"Hello, {input.name}!")

        app = create_app(MyEndpoint)
        with TestClient(app) as client:
            response = client.post("/", json={"name": "World"})
            assert response.status_code == 200
            assert response.json() == {"message": "Hello, World!"}

    def test_invalid_input_returns_422(self):
        class MyEndpoint:
            def run(self, input: Input) -> Output:
                return Output(message=f"Hello, {input.name}!")

        app = create_app(MyEndpoint)
        with TestClient(app) as client:
            response = client.post("/", json={"wrong_field": "value"})
            assert response.status_code == 422

    def test_missing_body_returns_422(self):
        class MyEndpoint:
            def run(self, input: Input) -> Output:
                return Output(message=f"Hello, {input.name}!")

        app = create_app(MyEndpoint)
        with TestClient(app) as client:
            response = client.post("/")
            assert response.status_code == 422


class TestSetupMethod:
    def test_setup_is_called_on_startup(self):
        class MyEndpoint:
            def setup(self):
                self.prefix = "Hi"

            def run(self, input: Input) -> Output:
                return Output(message=f"{self.prefix}, {input.name}!")

        app = create_app(MyEndpoint)
        with TestClient(app) as client:
            response = client.post("/", json={"name": "World"})
            assert response.status_code == 200
            assert response.json() == {"message": "Hi, World!"}

    def test_endpoint_without_setup_works(self):
        class MyEndpoint:
            def run(self, input: Input) -> Output:
                return Output(message=f"Hello, {input.name}!")

        app = create_app(MyEndpoint)
        with TestClient(app) as client:
            response = client.post("/", json={"name": "World"})
            assert response.status_code == 200


class TestErrorHandling:
    def test_exception_in_run_returns_500(self):
        class MyEndpoint:
            def run(self, input: Input) -> Output:
                raise ValueError("Something went wrong")

        app = create_app(MyEndpoint)
        with TestClient(app) as client:
            response = client.post("/", json={"name": "World"})
            assert response.status_code == 500
            assert "Something went wrong" in response.json()["detail"]

    def test_setup_failure_prevents_startup(self):
        from jarvis.exceptions import EndpointSetupError

        class MyEndpoint:
            def setup(self):
                raise RuntimeError("Setup failed!")

            def run(self, input: Input) -> Output:
                return Output(message=f"Hello, {input.name}!")

        app = create_app(MyEndpoint)
        with pytest.raises(EndpointSetupError) as exc_info:
            with TestClient(app):
                pass
        assert "Setup failed!" in str(exc_info.value)

    def test_invalid_json_returns_422_with_details(self):
        class MyEndpoint:
            def run(self, input: Input) -> Output:
                return Output(message=f"Hello, {input.name}!")

        app = create_app(MyEndpoint)
        with TestClient(app) as client:
            response = client.post("/", json={"wrong_field": "value"})
            assert response.status_code == 422
            # Verify validation error details are included
            assert "detail" in response.json()


class TestOpenAPIDocs:
    def test_openapi_docs_available(self):
        class MyEndpoint:
            _jarvis_endpoint_name = "greeter"

            def run(self, input: Input) -> Output:
                return Output(message=f"Hello, {input.name}!")

        app = create_app(MyEndpoint)
        client = TestClient(app)

        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json_has_correct_schema(self):
        class MyEndpoint:
            _jarvis_endpoint_name = "greeter"

            def run(self, input: Input) -> Output:
                return Output(message=f"Hello, {input.name}!")

        app = create_app(MyEndpoint)
        client = TestClient(app)

        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi = response.json()
        assert openapi["info"]["title"] == "greeter"
        assert "/" in openapi["paths"]
        assert "post" in openapi["paths"]["/"]
