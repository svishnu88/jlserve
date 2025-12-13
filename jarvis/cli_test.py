"""Unit tests for CLI argument parsing."""

import tempfile
from pathlib import Path

from typer.testing import CliRunner

from jarvis.cli import app

runner = CliRunner()


class TestDevCommand:
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

    def test_dev_no_endpoint_found(self):
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"# empty python file\nx = 1\n")
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])
            assert result.exit_code == 1
            assert "No endpoints found" in result.output
        finally:
            Path(temp_path).unlink()

    def test_dev_port_option_default(self):
        result = runner.invoke(app, ["dev", "--help"])
        assert "8000" in result.output

    def test_dev_port_option_short_flag(self):
        result = runner.invoke(app, ["dev", "--help"])
        assert "-p" in result.output
