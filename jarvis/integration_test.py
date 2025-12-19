"""End-to-end integration tests for multi-endpoint apps."""

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

import jarvis
from jarvis.decorator import _reset_registry
from jarvis.server import create_app


class TestCalculatorApp:
    """Integration test with the Calculator example from the issue."""

    def test_calculator_multi_endpoint_example(self):
        _reset_registry()

        class TwoNumbers(BaseModel):
            a: int
            b: int

        class Result(BaseModel):
            result: int

        @jarvis.app()
        class Calculator:
            def setup(self):
                self.operation_count = 0

            @jarvis.endpoint()
            def add(self, input: TwoNumbers) -> Result:
                self.operation_count += 1
                return Result(result=input.a + input.b)

            @jarvis.endpoint()
            def subtract(self, input: TwoNumbers) -> Result:
                self.operation_count += 1
                return Result(result=input.a - input.b)

        app = create_app(Calculator)

        with TestClient(app) as client:
            # Test add endpoint
            response = client.post("/add", json={"a": 5, "b": 3})
            assert response.status_code == 200
            assert response.json() == {"result": 8}

            # Test subtract endpoint
            response = client.post("/subtract", json={"a": 10, "b": 4})
            assert response.status_code == 200
            assert response.json() == {"result": 6}

            # Verify OpenAPI docs
            response = client.get("/openapi.json")
            assert response.status_code == 200
            openapi = response.json()
            assert openapi["info"]["title"] == "Calculator"
            assert "/add" in openapi["paths"]
            assert "/subtract" in openapi["paths"]


class TestMLApp:
    """Integration test with ML-like multi-endpoint app."""

    def test_text_analysis_app(self):
        _reset_registry()

        class TextInput(BaseModel):
            text: str

        class SentimentOutput(BaseModel):
            label: str
            score: float

        class LengthOutput(BaseModel):
            length: int
            word_count: int

        @jarvis.app()
        class TextAnalyzer:
            def setup(self):
                # Mock ML model loading
                self.sentiment_model = lambda text: ("POSITIVE", 0.95)
                self.calls = 0

            @jarvis.endpoint()
            def analyze_sentiment(self, input: TextInput) -> SentimentOutput:
                self.calls += 1
                label, score = self.sentiment_model(input.text)
                return SentimentOutput(label=label, score=score)

            @jarvis.endpoint()
            def get_length(self, input: TextInput) -> LengthOutput:
                self.calls += 1
                return LengthOutput(
                    length=len(input.text),
                    word_count=len(input.text.split())
                )

        app = create_app(TextAnalyzer)

        with TestClient(app) as client:
            # Test sentiment analysis
            response = client.post("/analyze_sentiment", json={"text": "I love this!"})
            assert response.status_code == 200
            data = response.json()
            assert data["label"] == "POSITIVE"
            assert data["score"] == 0.95

            # Test length analysis
            response = client.post("/get_length", json={"text": "Hello world"})
            assert response.status_code == 200
            data = response.json()
            assert data["length"] == 11
            assert data["word_count"] == 2


class TestSharedStateIntegration:
    """Integration tests for shared state across endpoints."""

    def test_ml_model_shared_across_endpoints(self):
        """Simulate an ML app where a model is loaded once and used by multiple endpoints."""
        _reset_registry()

        class Input(BaseModel):
            value: float

        class PredictionOutput(BaseModel):
            prediction: float

        class ModelInfoOutput(BaseModel):
            model_name: str
            predictions_made: int

        @jarvis.app()
        class MLService:
            def setup(self):
                # Simulate loading a heavy ML model
                self.model_name = "linear_model_v1"
                self.weight = 2.5
                self.bias = 1.0
                self.predictions_made = 0

            @jarvis.endpoint()
            def predict(self, input: Input) -> PredictionOutput:
                self.predictions_made += 1
                prediction = input.value * self.weight + self.bias
                return PredictionOutput(prediction=prediction)

            @jarvis.endpoint()
            def model_info(self, input: Input) -> ModelInfoOutput:
                return ModelInfoOutput(
                    model_name=self.model_name,
                    predictions_made=self.predictions_made
                )

        app = create_app(MLService)

        with TestClient(app) as client:
            # Make several predictions
            for x in [1.0, 2.0, 3.0]:
                response = client.post("/predict", json={"value": x})
                assert response.status_code == 200

            # Check model info reflects all predictions
            response = client.post("/model_info", json={"value": 0})
            assert response.status_code == 200
            data = response.json()
            assert data["model_name"] == "linear_model_v1"
            assert data["predictions_made"] == 3


class TestCustomPaths:
    """Integration tests for custom endpoint paths."""

    def test_custom_path_routing(self):
        _reset_registry()

        class NumberInput(BaseModel):
            n: int

        class NumberOutput(BaseModel):
            result: int

        @jarvis.app()
        class MathOperations:
            @jarvis.endpoint(path="/v1/double")
            def double(self, input: NumberInput) -> NumberOutput:
                return NumberOutput(result=input.n * 2)

            @jarvis.endpoint(path="/v1/triple")
            def triple(self, input: NumberInput) -> NumberOutput:
                return NumberOutput(result=input.n * 3)

            @jarvis.endpoint(path="/v2/quadruple")
            def quadruple(self, input: NumberInput) -> NumberOutput:
                return NumberOutput(result=input.n * 4)

        app = create_app(MathOperations)

        with TestClient(app) as client:
            assert client.post("/v1/double", json={"n": 5}).json() == {"result": 10}
            assert client.post("/v1/triple", json={"n": 5}).json() == {"result": 15}
            assert client.post("/v2/quadruple", json={"n": 5}).json() == {"result": 20}


class TestMinimalApp:
    """Verify success criteria: endpoint defined in minimal lines."""

    def test_minimal_multi_endpoint_app(self):
        """Demonstrate that a functional multi-endpoint app can be concise."""
        _reset_registry()

        class In(BaseModel):
            x: int

        class Out(BaseModel):
            y: int

        @jarvis.app()
        class Math:
            @jarvis.endpoint()
            def double(self, i: In) -> Out:
                return Out(y=i.x * 2)

            @jarvis.endpoint()
            def square(self, i: In) -> Out:
                return Out(y=i.x ** 2)

        app = create_app(Math)

        with TestClient(app) as client:
            assert client.post("/double", json={"x": 5}).json() == {"y": 10}
            assert client.post("/square", json={"x": 4}).json() == {"y": 16}
