# Jarvis SDK

A simple Python framework for creating ML inference endpoints with minimal boilerplate.

## Features

- **Simple API** - One decorator, one class, one method
- **Type-safe** - Pydantic models for input/output validation
- **Developer-friendly** - IDE autocomplete, typo detection, auto-generated docs
- **Fast startup** - Server ready in under 2 seconds

## Installation

```bash
pip install jarvis
```

Or with uv:

```bash
uv add jarvis
```

## Quick Start

Create an endpoint in `app.py`:

```python
import jarvis
from pydantic import BaseModel


class Input(BaseModel):
    name: str


class Output(BaseModel):
    message: str


@jarvis.endpoint(name="greeter")
class Greeter:
    def setup(self):
        self.prefix = "Hello"

    def run(self, input: Input) -> Output:
        return Output(message=f"{self.prefix}, {input.name}!")
```

Run the server:

```bash
jarvis dev app.py
```

Output:

```
Serving greeter at http://localhost:8000
Docs at http://localhost:8000/docs
```

Test the endpoint:

```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"name": "World"}'
```

Response:

```json
{"message": "Hello, World!"}
```

## API Reference

### `@jarvis.endpoint(name)`

Decorator that marks a class as a Jarvis endpoint.

| Parameter | Type  | Required | Description              |
|-----------|-------|----------|--------------------------|
| `name`    | `str` | Yes      | Name of the endpoint     |

### Class Methods

| Method            | Required | Description                                                                 |
|-------------------|----------|-----------------------------------------------------------------------------|
| `setup(self)`     | No       | Called once when server starts. Use for loading models, initializing resources. |
| `run(self, input) -> output` | Yes | Handles incoming requests. Must have type hints for input and output. |

### Input/Output Requirements

- Input must be a Pydantic `BaseModel` subclass
- Output must be a Pydantic `BaseModel` subclass
- Type hints are required on the `run()` method

## CLI Reference

### `jarvis dev <file>`

Runs the endpoint locally for development.

| Option   | Default | Description       |
|----------|---------|-------------------|
| `--port`, `-p` | `8000`  | Port to serve on  |

Example:

```bash
jarvis dev app.py --port 3000
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
| Missing `run()` method       | Error at startup: "Endpoint class must define a run() method" |
| Missing type hints on `run()` | Error at startup: "run() must have type hints for input and output" |
| Invalid input JSON           | 422 response with validation errors                   |
| Exception in `run()`         | 500 response with error message                       |
| Exception in `setup()`       | Server fails to start with error message              |

## Example: ML Inference

```python
import jarvis
from pydantic import BaseModel


class SentimentInput(BaseModel):
    text: str


class SentimentOutput(BaseModel):
    label: str
    score: float


@jarvis.endpoint(name="sentiment")
class SentimentAnalyzer:
    def setup(self):
        from transformers import pipeline
        self.pipe = pipeline("sentiment-analysis")

    def run(self, input: SentimentInput) -> SentimentOutput:
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
