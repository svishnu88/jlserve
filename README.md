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
| `gpu` | `str` | No | GPU type to deploy on, e.g. `"L4"` or `"H100"`. Default `None` (decided at deploy time). Ignored by `jlserve dev`. |
| `gpus_per_worker` | `int` | No | GPUs attached to one worker: `1`, `2`, `4` or `8`. Default `1`. |
| `min_workers` | `int` | No | Workers kept warm at all times, `0`–`100`. Default `0` (scale to zero). |
| `max_workers` | `int` | No | Upper bound on workers, `0`–`100`. Must be ≥ `min_workers`; the two cannot both be `0`. Default `1`. |
| `idle_timeout` | `int` | No | Seconds an idle worker stays up before shutdown, `0`–`86400`. Default `600`. |

The deploy settings are validated when the class is decorated and stored on it; `jlserve dev` ignores them. They describe how the app should run once deployed, and are read by the deploy tooling.

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

### `jlserve deploy <file>`

Deploys the app to JarvisLabs serverless. The file is validated locally first, then sent together with the deploy settings from `@jlserve.app()`. The command waits until the deployment is running and prints one URL per endpoint.

| Option | Env var | Default | Description |
|--------|---------|---------|-------------|
| `--token` | `JARVISLABS_API_TOKEN` | | Your JarvisLabs API token. Required. |
| `--gpu` | | from decorator | GPU type, e.g. `L4`. Required if the decorator has no `gpu`. |
| `--name`, `-n` | | app name | Deployment name. |
| `--endpoint` | `JLSERVE_ENDPOINT` | Noida service | Serverless service URL for the region. |
| `--hf-token` | `HF_TOKEN` | | Hugging Face token, for gated models. |
| `--wait/--no-wait` | | `--wait` | Wait for the deployment to reach `running`. |
| `--timeout` | | `900` | Seconds to wait before giving up. |

Example:

```bash
export JARVISLABS_API_TOKEN=...
jlserve deploy sd-turbo.py
```

Output:

```
Validating sd-turbo.py ...
App: SDTurbo  Endpoints: POST /generate
GPU: L4 x1  Workers: 0-1  Idle timeout: 300s
Requirements: diffusers, transformers, accelerate
Creating deployment at https://serverlessn.jarvislabs.net ...
Deployment id: 01K4...
  status: starting
  status: filesystem_created
  status: running

Deployment 01K4... is running.

Endpoints:
  https://serverlessn.jarvislabs.net/deployment/01K4.../generate
```

Calling an endpoint goes through the serverless service, so the request body is wrapped in `"input"` and the reply carries a request id to poll:

```bash
curl -X POST https://serverlessn.jarvislabs.net/deployment/01K4.../generate \
  -H "Authorization: Bearer $JARVISLABS_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": {"prompt": "a red bicycle on a beach"}}'
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
| `jlserve deploy` without a token or GPU type | Error before anything is sent           |
| Deployment fails on the platform | Error with the service's message, exit code 1     |

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
