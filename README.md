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
    def download_weights(self):
        """Download/prepare any resources (required method)."""
        pass  # No weights needed for this simple example

    def setup(self):
        """Initialize on server startup (required method)."""
        self.prefix = "Hello"

    @jlserve.endpoint()
    def greet(self, input: Input) -> Output:
        return Output(message=f"{self.prefix}, {input.name}!")
```

Run the server:

```bash
export JLSERVE_CACHE_DIR=/tmp/cache
mkdir -p $JLSERVE_CACHE_DIR
jlserve build app.py
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
| `download_weights(self)` | Yes | Called by `jlserve build`. Download and cache model weights to `JLSERVE_CACHE_DIR`. |
| `setup(self)`     | Yes      | Called once when server starts. Load models from cache. |
| `<endpoint_method>(self, input) -> output` | Yes | Endpoint methods decorated with `@jlserve.endpoint()`. Must have type hints for input and output. |

### Input/Output Requirements

- Input must be a Pydantic `BaseModel` subclass
- Output must be a Pydantic `BaseModel` subclass
- Type hints are required on endpoint methods

## CLI Reference

### `jlserve build <file>`

Builds the app by installing dependencies and downloading model weights to cache. Run this once before starting the server, or when dependencies/models change.

```bash
export JLSERVE_CACHE_DIR=/path/to/cache
jlserve build app.py
```

This command:
1. Validates that `JLSERVE_CACHE_DIR` is set
2. Installs Python dependencies (cached to `JLSERVE_CACHE_DIR`)
3. Calls `download_weights()` to cache model files
4. Creates a build marker for `dev` command

### `jlserve dev <file>`

Runs the app locally for development. Requires `jlserve build` to be run first.

| Option   | Default | Description       |
|----------|---------|-------------------|
| `--port`, `-p` | `8000`  | Port to serve on  |

Example:

```bash
jlserve dev app.py --port 3000
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JLSERVE_CACHE_DIR` | Yes | Directory for caching model weights and Python packages. Must be set before running `build` or `dev`. In containerized environments (like JarvisLabs), point this to a persistent volume to avoid re-downloading on restarts. |

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

## Weight Caching for Fast Startup

JLServe separates weight downloading from server startup for faster container restarts.

### The Pattern

```python
@jlserve.app()
class MyModel:
    def download_weights(self):
        """Download model weights to cache (called by 'jlserve build')"""
        # Download once, save to JLSERVE_CACHE_DIR
        model = download_model("my-model", cache_dir=os.getenv("JLSERVE_CACHE_DIR"))

    def setup(self):
        """Load model from cache (called on server startup)"""
        # Load from cache, don't re-download
        self.model = load_model("my-model", cache_dir=os.getenv("JLSERVE_CACHE_DIR"))

    @jlserve.endpoint()
    def predict(self, input: Input) -> Output:
        return self.model.run(input)
```

### Workflow

1. **Set cache directory** (point to persistent storage):
   ```bash
   export JLSERVE_CACHE_DIR=/workspace/cache
   ```

2. **Build once** (downloads weights and dependencies):
   ```bash
   jlserve build app.py
   ```

3. **Run server** (loads from cache, fast startup):
   ```bash
   jlserve dev app.py
   ```

On container restarts, skip step 2 - weights are already cached!

### Why Two Commands?

- **`build`**: Downloads weights to cache (run once, or when model changes)
- **`dev`**: Loads weights from cache (fast startup, run on every restart)

This pattern is essential for containerized deployments where you want to:
- Avoid re-downloading large model files on every restart
- Persist dependencies and weights across container lifecycles
- Optimize startup time in production environments

## Example: ML Inference

```python
import os
import jlserve
from pydantic import BaseModel


class SentimentInput(BaseModel):
    text: str


class SentimentOutput(BaseModel):
    label: str
    score: float


@jlserve.app(requirements=["transformers"])
class SentimentAnalyzer:
    def download_weights(self):
        """Download model to cache during build."""
        from transformers import pipeline
        # Downloads model files to HuggingFace cache
        # (transformers respects HF_HOME which can be set to JLSERVE_CACHE_DIR)
        pipeline("sentiment-analysis")

    def setup(self):
        """Load model from cache on server startup."""
        from transformers import pipeline
        # Loads from cache, no download needed
        self.pipe = pipeline("sentiment-analysis")

    @jlserve.endpoint()
    def analyze(self, input: SentimentInput) -> SentimentOutput:
        result = self.pipe(input.text)[0]
        return SentimentOutput(
            label=result["label"],
            score=result["score"]
        )
```

Run it:

```bash
export JLSERVE_CACHE_DIR=/workspace/cache
jlserve build app.py  # Downloads transformers model once
jlserve dev app.py    # Fast startup, loads from cache
```

## Development

Run tests:

```bash
uv run pytest
```

## License

MIT
