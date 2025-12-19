"""Unit tests for CLI argument parsing."""

import tempfile
from pathlib import Path

from typer.testing import CliRunner

from jarvis.cli import app

runner = CliRunner()


class TestDevCommand:
    """Tests for the dev command."""

    def test_help_shows_dev_command(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "dev" in result.output

    def test_dev_help_shows_options(self):
        result = runner.invoke(app, ["dev", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output
        assert "file" in result.output.lower()

    def test_dev_requires_file_argument(self):
        result = runner.invoke(app, ["dev"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "FILE" in result.output

    def test_dev_file_not_found(self):
        result = runner.invoke(app, ["dev", "nonexistent.py"])
        assert result.exit_code == 1
        assert "File not found" in result.output

    def test_dev_file_must_be_python(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"not python")
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])
            assert result.exit_code == 1
            assert "must be a Python file" in result.output
        finally:
            Path(temp_path).unlink()

    def test_dev_no_app_found(self):
        """Test error message when no @jarvis.app() decorated class is found."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"# empty python file\nx = 1\n")
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])
            assert result.exit_code == 1
            assert "No apps found" in result.output
            assert "@jarvis.app()" in result.output
        finally:
            Path(temp_path).unlink()

    def test_dev_app_with_no_endpoints(self):
        """Test error message when app has no @jarvis.endpoint() methods."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            code = b"""
import jarvis

@jarvis.app()
class EmptyApp:
    pass
"""
            f.write(code)
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])
            assert result.exit_code == 1
            assert "no endpoints" in result.output.lower()
            assert "@jarvis.endpoint()" in result.output
        finally:
            Path(temp_path).unlink()

    def test_dev_port_option_default(self):
        result = runner.invoke(app, ["dev", "--help"])
        assert "8000" in result.output

    def test_dev_port_option_short_flag(self):
        result = runner.invoke(app, ["dev", "--help"])
        assert "-p" in result.output


class TestDevCommandValidation:
    """Tests for dev command validation of apps."""

    def test_valid_app_imports_correctly(self):
        """Test that a valid multi-endpoint app can be imported and validated."""
        # This test verifies the import and validation logic works
        # without actually starting the server
        import importlib.util
        import sys

        from jarvis.decorator import clear_registry, get_endpoint_methods, get_registered_apps

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            code = b"""
import jarvis
from pydantic import BaseModel

class Input(BaseModel):
    value: int

class Output(BaseModel):
    result: int

@jarvis.app()
class Calculator:
    @jarvis.endpoint()
    def add(self, input: Input) -> Output:
        return Output(result=input.value + 1)

    @jarvis.endpoint()
    def subtract(self, input: Input) -> Output:
        return Output(result=input.value - 1)
"""
            f.write(code)
            temp_path = f.name

        try:
            clear_registry()
            spec = importlib.util.spec_from_file_location("test_module", temp_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules["test_module"] = module
            spec.loader.exec_module(module)

            apps = get_registered_apps()
            assert len(apps) == 1
            assert apps[0]._jarvis_app_name == "Calculator"

            methods = get_endpoint_methods(apps[0])
            assert len(methods) == 2
        finally:
            Path(temp_path).unlink()
            if "test_module" in sys.modules:
                del sys.modules["test_module"]
