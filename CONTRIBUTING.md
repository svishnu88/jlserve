# Contributing to JLServe

## Development Setup

```bash
# Clone the repository
git clone https://github.com/svishnu88/jlserve.git
cd jlserve

# Install dependencies
uv sync

# Run tests
uv run pytest
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run a specific test file
uv run pytest jlserve/decorator_test.py

# Run a specific test
uv run pytest jlserve/decorator_test.py::test_endpoint_decorator_registers_method

# Run with verbose output
uv run pytest -v
```

## Building and Publishing

### Building the Package

```bash
# Build distribution packages (creates dist/ folder)
uv build
```

This creates:
- `dist/jlserve-<version>-py3-none-any.whl` (wheel)
- `dist/jlserve-<version>.tar.gz` (source distribution)

### Testing the Build Locally

```bash
# Install the built wheel in a test environment
uv pip install dist/jlserve-<version>-py3-none-any.whl

# Or install in editable mode for development
uv pip install -e .
```

### Publishing to PyPI

#### First-Time Setup

1. Create accounts on [PyPI](https://pypi.org/account/register/) and [TestPyPI](https://test.pypi.org/account/register/)
2. Create an API token at https://pypi.org/manage/account/token/
3. Set the token as an environment variable:

```bash
export UV_PUBLISH_TOKEN=pypi-your-token-here
```

Or create a `~/.pypirc` file:

```ini
[pypi]
username = __token__
password = pypi-your-token-here

[testpypi]
username = __token__
password = pypi-your-token-here
```

#### Publishing Workflow

```bash
# 1. Update version in pyproject.toml
# Edit the version field (e.g., "0.1.0" -> "0.1.1")

# 2. Build the package
uv build

# 3. (Optional) Publish to TestPyPI first
uv publish --publish-url https://test.pypi.org/legacy/

# 4. (Optional) Test installation from TestPyPI
uv pip install --index-url https://test.pypi.org/simple/ jlserve

# 5. Publish to production PyPI
uv publish

# 6. Verify the package is available
uv pip install jlserve
```

#### Publishing with Credentials Directly

If you prefer not to use environment variables:

```bash
uv publish --token pypi-your-token-here
```

### Version Management

Update the version in `pyproject.toml` before each release:

```toml
[project]
version = "0.1.1"  # Update this
```

Version numbering follows [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes (e.g., 1.0.0 -> 2.0.0)
- **MINOR** version for backwards-compatible functionality (e.g., 0.1.0 -> 0.2.0)
- **PATCH** version for backwards-compatible bug fixes (e.g., 0.1.0 -> 0.1.1)

### Pre-release Checklist

Before publishing a new version:

- [ ] All tests pass: `uv run pytest`
- [ ] Version bumped in `pyproject.toml`
- [ ] CHANGELOG updated (if you maintain one)
- [ ] Commit and tag the release:
  ```bash
  git commit -am "Release v0.1.1"
  git tag v0.1.1
  git push origin main --tags
  ```
- [ ] Build succeeds: `uv build`
- [ ] Test on TestPyPI (optional)
- [ ] Publish to PyPI: `uv publish`

## Code Style

- Follow PEP 8 conventions
- Use type hints where possible
- Keep functions focused and small
- Write tests for new features

## Project Structure

```
jlserve/
├── jlserve/
│   ├── __init__.py      # Public API exports
│   ├── decorator.py     # @app() and @endpoint() decorators
│   ├── validator.py     # App structure validation
│   ├── server.py        # FastAPI app creation
│   ├── cli.py           # CLI commands
│   ├── exceptions.py    # Custom exceptions
│   ├── requirements.py  # Dependency management
│   └── *_test.py        # Test files
├── examples/            # Example apps
├── pyproject.toml       # Package metadata and dependencies
├── README.md            # User documentation
└── CONTRIBUTING.md      # This file
```

## Making Changes

1. Create a new branch for your feature/fix
2. Make your changes
3. Add tests for new functionality
4. Run tests: `uv run pytest`
5. Submit a pull request

## Questions?

Open an issue at https://github.com/svishnu88/jlserve/issues
