# JLServe

A simple Python framework for creating ML inference endpoints with minimal boilerplate.

## Features

- **Simple API** - Decorator-based pattern for defining apps and endpoints
- **Type-safe** - Pydantic models for input/output validation
- **Developer-friendly** - IDE autocomplete, typo detection, auto-generated docs
- **Fast startup** - Server ready in under 2 seconds

## Installation

```bash
pip install jlserve
```

Or with uv:

```bash
uv add jlserve
```

## Quick Start

Create an app in `app.py`:

```python
import jlserve
from pydantic import BaseModel


class Input(BaseModel):
    name: str


class Output(BaseModel):
    message: str


@jlserve.app()
class Greeter:
    def setup(self):
        self.prefix = "Hello"

    @jlserve.endpoint()
    def greet(self, input: Input) -> Output:
        return Output(message=f"{self.prefix}, {input.name}!")
```

Run the server:

```bash
jlserve dev app.py
```

Output:

```
Serving Greeter at http://localhost:8000
Docs at http://localhost:8000/docs

Endpoints: POST /greet
```

Test the endpoint:

```bash
curl -X POST http://localhost:8000/greet \
  -H "Content-Type: application/json" \
  -d '{"name": "World"}'
```

Response:

```json
{"message": "Hello, World!"}
```

## API Reference

### `@jlserve.app()`

Decorator that marks a class as a JLServe app. Only one app per module/deployment.

| Parameter | Type  | Required | Description              |
|-----------|-------|----------|--------------------------|
| `name`    | `str` | No       | Custom name for the app. Defaults to class name. |
| `requirements` | `list[str]` | No | Python dependencies to auto-install (e.g., `["torch", "transformers"]`) |

### `@jlserve.endpoint()`

Decorator that marks a method as an endpoint within the app class.

| Parameter | Type  | Required | Description              |
|-----------|-------|----------|--------------------------|
| `path`    | `str` | No       | Custom route path. Defaults to "/" + method name. |

### Class Methods

| Method            | Required | Description                                                                 |
|-------------------|----------|-----------------------------------------------------------------------------|
| `setup(self)`     | No       | Called once when server starts. Use for loading models, initializing resources. |
| `<endpoint_method>(self, input) -> output` | Yes | Endpoint methods decorated with `@jlserve.endpoint()`. Must have type hints for input and output. |

### Input/Output Requirements

- Input must be a Pydantic `BaseModel` subclass
- Output must be a Pydantic `BaseModel` subclass
- Type hints are required on endpoint methods

## CLI Reference

### `jlserve dev <file>`

Runs the app locally for development.

| Option   | Default | Description       |
|----------|---------|-------------------|
| `--port`, `-p` | `8000`  | Port to serve on  |

Example:

```bash
jlserve dev app.py --port 3000
```

## Auto-Generated Features

| Feature            | Description                              |
|--------------------|------------------------------------------|
| OpenAPI docs       | Available at `/docs`                     |
| Request validation | Invalid input returns 422 with details   |
| JSON serialization | Automatic based on Pydantic models       |

## Error Handling

| Error                        | Behavior                                              |
|------------------------------|-------------------------------------------------------|
| No `@jlserve.app()` class    | Error at startup: "No app found. Did you decorate a class with @jlserve.app()?" |
| No endpoint methods          | Error at startup: "App has no endpoints. Add methods decorated with @jlserve.endpoint()." |
| Missing type hints on endpoint methods | Error at startup: Validation error with details |
| Invalid input JSON           | 422 response with validation errors                   |
| Exception in endpoint method | 500 response with error message                       |
| Exception in `setup()`       | Server fails to start with error message              |

## Example: ML Inference

```python
import jlserve
from pydantic import BaseModel


class SentimentInput(BaseModel):
    text: str


class SentimentOutput(BaseModel):
    label: str
    score: float


@jlserve.app(requirements=["transformers"])
class SentimentAnalyzer:
    def setup(self):
        from transformers import pipeline
        self.pipe = pipeline("sentiment-analysis")

    @jlserve.endpoint()
    def analyze(self, input: SentimentInput) -> SentimentOutput:
        result = self.pipe(input.text)[0]
        return SentimentOutput(
            label=result["label"],
            score=result["score"]
        )
```

## Development

Run tests:

```bash
uv run pytest
```

## License

MIT
