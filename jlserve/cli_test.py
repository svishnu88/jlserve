"""Unit tests for CLI argument parsing."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jlserve.cli import app

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
        """Test error message when no @jlserve.app() decorated class is found."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"# empty python file\nx = 1\n")
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])
            assert result.exit_code == 1
            assert "No app found" in result.output
            assert "@jlserve.app()" in result.output
        finally:
            Path(temp_path).unlink()

    def test_dev_app_with_no_endpoints(self):
        """Test error message when app has no @jlserve.endpoint() methods."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            code = b"""
import jlserve

@jlserve.app()
class EmptyApp:
    pass
"""
            f.write(code)
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])
            assert result.exit_code == 1
            assert "no endpoints" in result.output.lower()
            assert "@jlserve.endpoint()" in result.output
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

        from jlserve.decorator import _reset_registry, get_endpoint_methods, get_registered_app

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            code = b"""
import jlserve
from pydantic import BaseModel

class Input(BaseModel):
    value: int

class Output(BaseModel):
    result: int

@jlserve.app()
class Calculator:
    @jlserve.endpoint()
    def add(self, input: Input) -> Output:
        return Output(result=input.value + 1)

    @jlserve.endpoint()
    def subtract(self, input: Input) -> Output:
        return Output(result=input.value - 1)
"""
            f.write(code)
            temp_path = f.name

        try:
            _reset_registry()
            spec = importlib.util.spec_from_file_location("test_module", temp_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules["test_module"] = module
            spec.loader.exec_module(module)

            app_cls = get_registered_app()
            assert app_cls is not None
            assert app_cls._jlserve_app_name == "Calculator"

            methods = get_endpoint_methods(app_cls)
            assert len(methods) == 2
        finally:
            Path(temp_path).unlink()
            if "test_module" in sys.modules:
                del sys.modules["test_module"]


class TestDevCommandRequirements:
    """Tests for dev command with requirements parameter."""

    @patch("jlserve.cli.subprocess.run")
    @patch("jlserve.cli.uvicorn.run")
    def test_dev_installs_requirements(self, mock_uvicorn, mock_subprocess):
        """Test that dev command installs requirements before starting server."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve
from pydantic import BaseModel

class Input(BaseModel):
    value: int

class Output(BaseModel):
    result: int

@jlserve.app(requirements=["torch", "numpy>=1.24"])
class MyModel:
    @jlserve.endpoint()
    def predict(self, input: Input) -> Output:
        return Output(result=input.value * 2)
""")
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])

            # Verify subprocess.run was called with correct args
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0][0]
            assert call_args[0] == "uv"
            assert call_args[1] == "pip"
            assert call_args[2] == "install"
            assert "torch" in call_args
            assert "numpy>=1.24" in call_args

            # Verify uvicorn was started (server logic)
            assert mock_uvicorn.called
        finally:
            Path(temp_path).unlink()

    @patch("jlserve.cli.subprocess.run")
    @patch("jlserve.cli.uvicorn.run")
    def test_dev_no_requirements_skips_install(self, mock_uvicorn, mock_subprocess):
        """Test that dev command skips install when no requirements specified."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve
from pydantic import BaseModel

class Input(BaseModel):
    value: int

class Output(BaseModel):
    result: int

@jlserve.app()
class MyModel:
    @jlserve.endpoint()
    def predict(self, input: Input) -> Output:
        return Output(result=input.value * 2)
""")
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])

            # Verify subprocess.run was NOT called
            mock_subprocess.assert_not_called()

            # Verify uvicorn was still started
            assert mock_uvicorn.called
        finally:
            Path(temp_path).unlink()

    @patch("jlserve.cli.subprocess.run")
    @patch("jlserve.cli.uvicorn.run")
    def test_dev_empty_requirements_skips_install(self, mock_uvicorn, mock_subprocess):
        """Test that dev command skips install when requirements list is empty."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve
from pydantic import BaseModel

class Input(BaseModel):
    value: int

class Output(BaseModel):
    result: int

@jlserve.app(requirements=[])
class MyModel:
    @jlserve.endpoint()
    def predict(self, input: Input) -> Output:
        return Output(result=input.value * 2)
""")
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])

            # Verify subprocess.run was NOT called
            mock_subprocess.assert_not_called()

            # Verify uvicorn was still started
            assert mock_uvicorn.called
        finally:
            Path(temp_path).unlink()

    @patch("jlserve.cli.uvicorn.run")
    def test_dev_handles_syntax_error_in_file(self, mock_uvicorn):
        """Test that dev command handles syntax errors gracefully."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("this is not valid python syntax }{[")
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])
            assert result.exit_code == 1
            assert "Invalid Python syntax" in result.output

            # Verify uvicorn was NOT started
            mock_uvicorn.assert_not_called()
        finally:
            Path(temp_path).unlink()

    @patch("jlserve.cli.subprocess.run")
    @patch("jlserve.cli.uvicorn.run")
    def test_dev_handles_subprocess_error(self, mock_uvicorn, mock_subprocess):
        """Test that dev command handles pip install failures."""
        from subprocess import CalledProcessError

        mock_subprocess.side_effect = CalledProcessError(1, "uv pip install")

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve
from pydantic import BaseModel

class Input(BaseModel):
    value: int

class Output(BaseModel):
    result: int

@jlserve.app(requirements=["nonexistent-package-xyz"])
class MyModel:
    @jlserve.endpoint()
    def predict(self, input: Input) -> Output:
        return Output(result=input.value * 2)
""")
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])
            assert result.exit_code == 1
            assert "Failed to install requirements" in result.output

            # Verify uvicorn was NOT started
            mock_uvicorn.assert_not_called()
        finally:
            Path(temp_path).unlink()

    @patch("jlserve.cli.subprocess.run")
    @patch("jlserve.cli.uvicorn.run")
    def test_dev_handles_uv_not_found(self, mock_uvicorn, mock_subprocess):
        """Test that dev command handles missing uv command."""
        mock_subprocess.side_effect = FileNotFoundError()

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve
from pydantic import BaseModel

class Input(BaseModel):
    value: int

class Output(BaseModel):
    result: int

@jlserve.app(requirements=["torch"])
class MyModel:
    @jlserve.endpoint()
    def predict(self, input: Input) -> Output:
        return Output(result=input.value * 2)
""")
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])
            assert result.exit_code == 1
            assert "'uv' command not found" in result.output

            # Verify uvicorn was NOT started
            mock_uvicorn.assert_not_called()
        finally:
            Path(temp_path).unlink()

    @patch("jlserve.cli.subprocess.run")
    @patch("jlserve.cli.uvicorn.run")
    def test_dev_extracts_requirements_before_import(self, mock_uvicorn, mock_subprocess):
        """Test that requirements are extracted via AST before importing (chicken-and-egg fix)."""
        # This file has imports that would fail if not installed
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
# These imports would fail if packages aren't installed
# import torch
# import transformers

import jlserve
from pydantic import BaseModel

class Input(BaseModel):
    value: int

class Output(BaseModel):
    result: int

@jlserve.app(requirements=["torch", "transformers"])
class MyModel:
    @jlserve.endpoint()
    def predict(self, input: Input) -> Output:
        return Output(result=input.value * 2)
""")
            temp_path = f.name

        try:
            result = runner.invoke(app, ["dev", temp_path])

            # Verify requirements were extracted and install attempted
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0][0]
            assert "torch" in call_args
            assert "transformers" in call_args

            # The key test: extraction happened via AST, not via import
            # If we had imported the file first, the commented imports would fail
        finally:
            Path(temp_path).unlink()


VALID_APP = b'''
import jlserve
from pydantic import BaseModel


class Input(BaseModel):
    x: int


class Output(BaseModel):
    y: int


@jlserve.app(requirements=["torch"], gpu="L4", min_workers=0, max_workers=2, idle_timeout=120)
class Doubler:
    @jlserve.endpoint()
    def double(self, input: Input) -> Output:
        return Output(y=input.x * 2)
'''


class TestDeployCommand:
    """Tests for the deploy command with the service client mocked."""

    @staticmethod
    def write_app(source: bytes = VALID_APP) -> str:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(source)
            return f.name

    def test_help_shows_deploy_command(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "deploy" in result.output

    def test_deploy_requires_token(self, monkeypatch):
        monkeypatch.delenv("JARVISLABS_API_TOKEN", raising=False)
        path = self.write_app()
        try:
            result = runner.invoke(app, ["deploy", path])
            assert result.exit_code == 1
            assert "No API token" in result.output
        finally:
            Path(path).unlink()

    def test_deploy_requires_gpu(self):
        path = self.write_app(VALID_APP.replace(b'gpu="L4", ', b""))
        try:
            result = runner.invoke(app, ["deploy", path, "--token", "t"])
            assert result.exit_code == 1
            assert "No GPU type" in result.output
        finally:
            Path(path).unlink()

    def test_deploy_validation_error_is_one_line(self):
        path = self.write_app(VALID_APP.replace(b"input: Input", b"input"))
        try:
            result = runner.invoke(app, ["deploy", path, "--token", "t"])
            assert result.exit_code == 1
            assert "Error: Endpoint method double() must have a type hint" in result.output
            assert "Traceback" not in result.output
        finally:
            Path(path).unlink()

    @patch("jlserve.cli.ServerlessClient")
    def test_deploy_success_prints_urls(self, mock_client_cls):
        client = MagicMock()
        client.__enter__.return_value = client
        client.create.return_value = {"deployment_id": "01DEP", "region": "noida"}
        client.status.side_effect = [{"status": "starting"}, {"status": "running"}]
        mock_client_cls.return_value = client

        path = self.write_app()
        try:
            with patch("jlserve.deploy.time.sleep"):
                result = runner.invoke(
                    app, ["deploy", path, "--token", "t", "--endpoint", "https://svc.example"],
                )
        finally:
            Path(path).unlink()

        assert result.exit_code == 0, result.output
        mock_client_cls.assert_called_once_with("https://svc.example", "t")
        payload, sent_file = client.create.call_args.args
        assert payload["framework"] == "jlserve"
        assert payload["gpus_to_use"] == {"gpus": ["L4"]}
        assert payload["max_workers"] == 2
        assert payload["args"]["requirements"] == ["torch"]
        assert str(sent_file) == path
        assert "status: starting" in result.output
        assert "status: running" in result.output
        assert "https://svc.example/deployment/01DEP/double" in result.output
        assert "Deployment 01DEP is running" in result.output

    @patch("jlserve.cli.ServerlessClient")
    def test_deploy_no_wait_skips_polling(self, mock_client_cls):
        client = MagicMock()
        client.__enter__.return_value = client
        client.create.return_value = {"deployment_id": "01DEP", "region": "noida"}
        mock_client_cls.return_value = client

        path = self.write_app()
        try:
            result = runner.invoke(app, ["deploy", path, "--token", "t", "--no-wait"])
        finally:
            Path(path).unlink()

        assert result.exit_code == 0, result.output
        client.status.assert_not_called()
        assert "Not waiting" in result.output
        assert "/deployment/01DEP/double" in result.output

    @patch("jlserve.cli.ServerlessClient")
    def test_deploy_failed_shows_service_error(self, mock_client_cls):
        client = MagicMock()
        client.__enter__.return_value = client
        client.create.return_value = {"deployment_id": "01DEP", "region": "noida"}
        client.status.return_value = {"status": "failed"}
        client.describe.return_value = {"status": "failed", "error_message": "no GPU available"}
        mock_client_cls.return_value = client

        path = self.write_app()
        try:
            result = runner.invoke(app, ["deploy", path, "--token", "t"])
        finally:
            Path(path).unlink()

        assert result.exit_code == 1
        assert "Deployment 01DEP failed: no GPU available" in result.output

    @patch("jlserve.cli.ServerlessClient")
    def test_deploy_create_error_from_service(self, mock_client_cls):
        from jlserve.deploy import DeployError

        client = MagicMock()
        client.__enter__.return_value = client
        client.create.side_effect = DeployError("Could not create deployment: 400 GPU types ['L4'] are not available")
        mock_client_cls.return_value = client

        path = self.write_app()
        try:
            result = runner.invoke(app, ["deploy", path, "--token", "t"])
        finally:
            Path(path).unlink()

        assert result.exit_code == 1
        assert "400 GPU types" in result.output
        client.status.assert_not_called()

    @patch("jlserve.cli.subprocess.run")
    def test_dev_validation_error_is_one_line(self, mock_subprocess):
        """The shared loader also gives dev a clean message instead of a traceback."""
        path = self.write_app(VALID_APP.replace(b"input: Input", b"input"))
        try:
            result = runner.invoke(app, ["dev", path])
            mock_subprocess.assert_called_once()
            assert result.exit_code == 1
            assert "Error: Endpoint method double() must have a type hint" in result.output
            assert "Traceback" not in result.output
        finally:
            Path(path).unlink()
