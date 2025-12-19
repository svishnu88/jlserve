# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jarvis SDK is a minimal Python framework for defining ML/inference endpoints with a decorator-based pattern. It uses a single-app, multi-endpoint architecture optimized for ML inference deployments where one deployment = one model.

## Commands

```bash
# Install dependencies
uv sync

# Run development server
uv run jarvis dev <file.py> [--port PORT]

# Run all tests
uv run pytest

# Run a single test file
uv run pytest jarvis/decorator_test.py

# Run a specific test
uv run pytest jarvis/decorator_test.py::test_endpoint_decorator_registers_method
```

## Architecture

### Core Pattern

Single `@jarvis.app()` class with multiple `@jarvis.endpoint()` methods:

```python
@jarvis.app()
class MyModel:
    def setup(self):          # Called once at startup (load model here)
        self.model = load_model()

    @jarvis.endpoint()        # POST /predict
    def predict(self, input: InputModel) -> OutputModel:
        return self.model.run(input)
```

### Key Components

- **`jarvis/decorator.py`** - `@app()` and `@endpoint()` decorators with single-app registry enforcement
- **`jarvis/validator.py`** - Validates app structure, Pydantic type hints, and duplicate paths
- **`jarvis/server.py`** - Creates FastAPI app with POST routes and lifespan handler for `setup()`
- **`jarvis/cli.py`** - `jarvis dev` command using Typer

### Design Constraints

- Only one `@jarvis.app()` class allowed per deployment (raises `MultipleAppsError`)
- All endpoint inputs/outputs must be Pydantic BaseModel subclasses
- Endpoint methods require type hints for both input parameter and return type
- The app instance is created once and reused across all requests
