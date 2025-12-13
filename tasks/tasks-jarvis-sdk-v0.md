## Relevant Files

- `jarvis/__init__.py` - Main module entry point, exports the `endpoint` decorator
- `jarvis/decorator.py` - Contains the `@jarvis.endpoint()` decorator implementation
- `jarvis/decorator_test.py` - Unit tests for the decorator
- `jarvis/validator.py` - Validation logic for endpoint classes (run method, type hints)
- `jarvis/validator_test.py` - Unit tests for validation logic
- `jarvis/server.py` - FastAPI server integration and request handling
- `jarvis/server_test.py` - Unit tests for server integration
- `jarvis/cli.py` - CLI implementation for `jarvis dev` command
- `jarvis/cli_test.py` - Unit tests for CLI
- `jarvis/exceptions.py` - Custom exception classes for error handling
- `pyproject.toml` - Project configuration and dependencies
- `README.md` - Usage documentation and examples

### Notes

- Unit tests should typically be placed alongside the code files they are testing (e.g., `decorator.py` and `decorator_test.py` in the same directory).
- Use `pytest` to run tests. Running without a path executes all tests found by the pytest configuration.

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:
- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch for this feature (e.g., `git checkout -b feature/jarvis-sdk-v0`)

- [x] 1.0 Set up project structure and dependencies
  - [x] 1.1 Create the `jarvis/` package directory with `__init__.py`
  - [x] 1.2 Create `pyproject.toml` with project metadata and dependencies (FastAPI, Pydantic, Uvicorn, Typer/Click)
  - [x] 1.3 Set up a virtual environment and install dependencies
  - [x] 1.4 Configure pytest in `pyproject.toml` for running tests
  - [x] 1.5 Create `jarvis/exceptions.py` with custom exception classes (e.g., `EndpointValidationError`)

- [x] 2.0 Implement the `@jarvis.endpoint()` decorator
  - [x] 2.1 Create `jarvis/decorator.py` with the `endpoint` function that accepts a `name` parameter
  - [x] 2.2 Implement the decorator to store endpoint metadata on the decorated class (e.g., `_jarvis_endpoint_name`)
  - [x] 2.3 Create a registry to track all decorated endpoint classes for later discovery
  - [x] 2.4 Export the `endpoint` decorator from `jarvis/__init__.py` so users can call `@jarvis.endpoint()`
  - [x] 2.5 Write unit tests in `jarvis/decorator_test.py` to verify decorator behavior

- [x] 3.0 Implement endpoint validation logic
  - [x] 3.1 Create `jarvis/validator.py` with validation functions
  - [x] 3.2 Implement check for `run()` method existence on the endpoint class
  - [x] 3.3 Implement check for type hints on `run()` method (input parameter and return type)
  - [x] 3.4 Implement check that input type hint is a Pydantic `BaseModel` subclass
  - [x] 3.5 Implement check that return type hint is a Pydantic `BaseModel` subclass
  - [x] 3.6 Raise clear error messages for each validation failure (as specified in PRD)
  - [x] 3.7 Write unit tests in `jarvis/validator_test.py` for all validation scenarios

- [x] 4.0 Implement the FastAPI server integration
  - [x] 4.1 Create `jarvis/server.py` with a function to create a FastAPI app from an endpoint class
  - [x] 4.2 Implement instantiation of the endpoint class when the server starts
  - [x] 4.3 Implement calling `setup()` method (if defined) during server startup using FastAPI lifespan
  - [x] 4.4 Create a POST route at `/` that calls the endpoint's `run()` method
  - [x] 4.5 Wire up request body validation using the input Pydantic model from type hints
  - [x] 4.6 Wire up response serialization using the output Pydantic model from type hints
  - [x] 4.7 Ensure OpenAPI docs are auto-generated at `/docs` with correct schema
  - [x] 4.8 Write unit tests in `jarvis/server_test.py` using FastAPI TestClient

- [x] 5.0 Implement the `jarvis dev` CLI command
  - [x] 5.1 Create `jarvis/cli.py` using Typer (or Click) for CLI framework
  - [x] 5.2 Implement the `dev` command that accepts a file path argument
  - [x] 5.3 Implement dynamic loading of the user's Python file to discover endpoint classes
  - [x] 5.4 Add `--port` option with default value of `8000`
  - [x] 5.5 Start Uvicorn server programmatically with the generated FastAPI app
  - [x] 5.6 Print startup message: "Serving {name} at http://localhost:{port}" and "Docs at http://localhost:{port}/docs"
  - [x] 5.7 Configure the CLI entry point in `pyproject.toml` so `jarvis` command is available after install
  - [x] 5.8 Write unit tests in `jarvis/cli_test.py` for CLI argument parsing

- [x] 6.0 Add error handling and validation responses
  - [x] 6.1 Ensure FastAPI returns 422 with validation details for invalid input JSON
  - [x] 6.2 Implement exception handling in the route to catch exceptions from `run()` and return 500 with error message
  - [x] 6.3 Implement error handling for `setup()` failures that prevents server from starting and shows error message
  - [x] 6.4 Add integration tests for error scenarios (invalid JSON, exceptions in run/setup)

- [x] 7.0 Write tests and documentation
  - [x] 7.1 Create end-to-end integration test with a sample endpoint (like the Greeter example from PRD)
  - [x] 7.2 Create integration test with ML-like endpoint (mocking the model)
  - [x] 7.3 Verify all success criteria from PRD are met (< 10 lines, < 2 seconds startup, typo detection, autocomplete, OpenAPI)
  - [x] 7.4 Write `README.md` with installation instructions, quick start example, and API reference
  - [x] 7.5 Run full test suite and ensure all tests pass
