## Relevant Files

- `jarvis/decorator.py` - Contains the decorator implementations; needs new `app()` decorator and method-level `endpoint()` decorator
- `jarvis/decorator_test.py` - Unit tests for decorator functionality
- `jarvis/validator.py` - Validation logic; needs updates to validate method-level endpoints
- `jarvis/validator_test.py` - Unit tests for validation logic
- `jarvis/server.py` - FastAPI server integration; needs multi-route registration support
- `jarvis/server_test.py` - Unit tests for server functionality
- `jarvis/cli.py` - CLI implementation; needs updated messaging for multi-endpoint apps
- `jarvis/cli_test.py` - Unit tests for CLI
- `jarvis/exceptions.py` - Custom exceptions; may need new exception types
- `jarvis/__init__.py` - Package exports; needs to export new `app` decorator
- `jarvis/integration_test.py` - Integration tests for end-to-end scenarios
- `example_app.py` - Example app; update to demonstrate multi-endpoint usage

### Notes

- Unit tests should typically be placed alongside the code files they are testing (e.g., `decorator.py` and `decorator_test.py` in the same directory).
- Use `pytest` to run tests: `pytest jarvis/` or `pytest jarvis/decorator_test.py` for specific files.
- The current branch is `feature/jarvis-sdk-v0` - no need to create a new feature branch.
- **Backward compatibility is NOT required** - the old single-endpoint `@endpoint()` class decorator will be removed entirely.

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:
- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x] 1.0 Implement the `@jarvis.app()` class decorator
  - [x] 1.1 Remove the old class-level `endpoint()` decorator from `decorator.py`
  - [x] 1.2 Remove `_endpoint_registry` and replace with `_app_registry`
  - [x] 1.3 Add new `app()` decorator function that marks a class as a Jarvis app
  - [x] 1.4 Store app metadata on the class (e.g., `_jarvis_app = True`, `_jarvis_app_name`)
  - [x] 1.5 Rename `get_registered_endpoints()` to `get_registered_apps()`

- [x] 2.0 Implement the `@jarvis.endpoint()` method-level decorator
  - [x] 2.1 Create new `endpoint()` decorator that works on methods (not classes)
  - [x] 2.2 Mark decorated methods with `_jarvis_endpoint = True` and store route path
  - [x] 2.3 Add optional `path` parameter to `endpoint()` for custom route paths (defaults to method name)
  - [x] 2.4 Create helper function `get_endpoint_methods(cls)` to retrieve all endpoint-decorated methods from an app class
  - [x] 2.5 Ensure method-level decorator preserves method signature and docstrings using `functools.wraps`

- [x] 3.0 Update validation logic for multi-endpoint apps
  - [x] 3.1 Remove old `validate_endpoint()`, `validate_has_run_method()`, `validate_run_type_hints()` functions
  - [x] 3.2 Remove old `get_input_type()` and `get_output_type()` functions
  - [x] 3.3 Create new `validate_app()` function for validating app-decorated classes
  - [x] 3.4 Validate that app classes have at least one `@endpoint()` decorated method
  - [x] 3.5 For each endpoint method, validate input parameter has Pydantic BaseModel type hint
  - [x] 3.6 For each endpoint method, validate return type is a Pydantic BaseModel subclass
  - [x] 3.7 Add `get_method_input_type(method)` and `get_method_output_type(method)` helper functions
  - [x] 3.8 Validate that endpoint routes don't conflict (no duplicate paths)

- [x] 4.0 Update server to handle multi-route registration
  - [x] 4.1 Remove old `create_app()` implementation that expects a `run()` method
  - [x] 4.2 Create new `create_app()` that works with `@app()` decorated classes
  - [x] 4.3 Implement single app instance creation with shared state across all endpoints
  - [x] 4.4 Call `setup()` method once during lifespan startup if it exists
  - [x] 4.5 Register a POST route for each `@endpoint()` decorated method (e.g., `POST /add`, `POST /subtract`)
  - [x] 4.6 Each route handler should call the corresponding method on the shared instance

- [x] 5.0 Update CLI messaging and multi-endpoint handling
  - [x] 5.1 Update `dev` command to use `get_registered_apps()` instead of `get_registered_endpoints()`
  - [x] 5.2 Print all available routes on startup (e.g., "Endpoints: POST /add, POST /subtract")
  - [x] 5.3 Update error messages to reference `@jarvis.app()` and `@jarvis.endpoint()` decorators

- [x] 6.0 Update test coverage
  - [x] 6.1 Remove old class-level `@endpoint()` tests from `decorator_test.py`
  - [x] 6.2 Add tests for `@app()` decorator registration and metadata in `decorator_test.py`
  - [x] 6.3 Add tests for method-level `@endpoint()` decorator in `decorator_test.py`
  - [x] 6.4 Add tests for custom route paths via `@endpoint(path="/custom")` in `decorator_test.py`
  - [x] 6.5 Remove old `run()` method validation tests from `validator_test.py`
  - [x] 6.6 Add validation tests for multi-endpoint apps in `validator_test.py`
  - [x] 6.7 Add tests for missing/invalid Pydantic models on endpoint methods in `validator_test.py`
  - [x] 6.8 Remove old single-endpoint server tests from `server_test.py`
  - [x] 6.9 Add server tests for multi-route registration in `server_test.py`
  - [x] 6.10 Add tests verifying shared state across endpoints in `server_test.py`
  - [x] 6.11 Update integration tests in `integration_test.py` for multi-endpoint app lifecycle
  - [x] 6.12 Update CLI tests in `cli_test.py` for new decorator pattern

- [x] 7.0 Update exports and documentation
  - [x] 7.1 Update `jarvis/__init__.py` to export both `app` and `endpoint` decorators
  - [x] 7.2 Update `example_app.py` to demonstrate multi-endpoint Calculator example from the issue
  - [x] 7.3 Ensure all new public functions have proper docstrings
