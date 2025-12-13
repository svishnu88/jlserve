"""End-to-end integration tests."""

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

import jarvis
from jarvis.decorator import clear_registry
from jarvis.server import create_app


class TestGreeterEndpoint:
    """Integration test with the Greeter example from PRD."""

    def test_greeter_example(self):
        clear_registry()

        class Input(BaseModel):
            name: str

        class Output(BaseModel):
            message: str

        @jarvis.endpoint()
        class Greeter:
            def setup(self):
                self.prefix = "Hello"

            def run(self, input: Input) -> Output:
                return Output(message=f"{self.prefix}, {input.name}!")

        app = create_app(Greeter)

        with TestClient(app) as client:
            # Test the endpoint
            response = client.post("/", json={"name": "Vishnu"})
            assert response.status_code == 200
            assert response.json() == {"message": "Hello, Vishnu!"}

            # Verify OpenAPI docs
            response = client.get("/openapi.json")
            assert response.status_code == 200
            assert response.json()["info"]["title"] == "Greeter"

    def test_greeter_without_setup(self):
        clear_registry()

        class Input(BaseModel):
            name: str

        class Output(BaseModel):
            message: str

        @jarvis.endpoint()
        class SimpleGreeter:
            def run(self, input: Input) -> Output:
                return Output(message=f"Hi, {input.name}!")

        app = create_app(SimpleGreeter)

        with TestClient(app) as client:
            response = client.post("/", json={"name": "World"})
            assert response.status_code == 200
            assert response.json() == {"message": "Hi, World!"}


class TestMLEndpoint:
    """Integration test with ML-like endpoint (mocking the model)."""

    def test_sentiment_analyzer(self):
        clear_registry()

        class SentimentInput(BaseModel):
            text: str

        class SentimentOutput(BaseModel):
            label: str
            score: float

        @jarvis.endpoint()
        class SentimentAnalyzer:
            def setup(self):
                # Mock the ML pipeline
                self.pipe = lambda text: [{"label": "POSITIVE", "score": 0.95}]

            def run(self, input: SentimentInput) -> SentimentOutput:
                result = self.pipe(input.text)[0]
                return SentimentOutput(
                    label=result["label"],
                    score=result["score"]
                )

        app = create_app(SentimentAnalyzer)

        with TestClient(app) as client:
            response = client.post("/", json={"text": "I love this product!"})
            assert response.status_code == 200
            data = response.json()
            assert data["label"] == "POSITIVE"
            assert data["score"] == 0.95

    def test_text_classifier(self):
        clear_registry()

        class ClassifierInput(BaseModel):
            text: str

        class ClassifierOutput(BaseModel):
            category: str
            confidence: float

        @jarvis.endpoint()
        class TextClassifier:
            def setup(self):
                # Mock categories
                self.categories = ["tech", "sports", "politics"]

            def run(self, input: ClassifierInput) -> ClassifierOutput:
                # Simple mock classification
                if "python" in input.text.lower():
                    return ClassifierOutput(category="tech", confidence=0.9)
                return ClassifierOutput(category="general", confidence=0.5)

        app = create_app(TextClassifier)

        with TestClient(app) as client:
            response = client.post("/", json={"text": "Python is great!"})
            assert response.status_code == 200
            data = response.json()
            assert data["category"] == "tech"
            assert data["confidence"] == 0.9


class TestEndpointCodeLines:
    """Verify success criteria: endpoint defined in <10 lines."""

    def test_minimal_endpoint(self):
        """Demonstrate that a functional endpoint can be defined in under 10 lines."""
        clear_registry()

        # Lines 1-2: Pydantic models
        class In(BaseModel):
            x: int

        class Out(BaseModel):
            y: int

        # Lines 3-6: Endpoint class (4 lines)
        @jarvis.endpoint()
        class Doubler:
            def run(self, input: In) -> Out:
                return Out(y=input.x * 2)

        # Total: 6 lines for a functional endpoint
        app = create_app(Doubler)

        with TestClient(app) as client:
            response = client.post("/", json={"x": 5})
            assert response.status_code == 200
            assert response.json() == {"y": 10}
