"""Tests for the example apps shipped in the repo root.

The examples load real models in setup(), which needs a GPU and several GB of
weights. These tests stop short of that: they import the file, check the app
structure validates, and check the input bounds and deploy settings. That is
what `jlserve dev` checks before it starts the server.
"""

import importlib.util
from pathlib import Path

import pytest
from pydantic import ValidationError

from jlserve.decorator import _reset_registry, get_deploy_settings, get_registered_app
from jlserve.requirements import extract_requirements_from_file
from jlserve.validator import get_method_input_type, validate_app

REPO_ROOT = Path(__file__).resolve().parent.parent
SD_TURBO = REPO_ROOT / "sd-turbo.py"


def _load_example(path: Path):
    """Import an example file by path and return the app class it registers."""
    _reset_registry()
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return get_registered_app()


@pytest.fixture
def sd_turbo():
    cls = _load_example(SD_TURBO)
    yield cls
    _reset_registry()


class TestSDTurboExample:
    """The sd-turbo example must validate without loading the model."""

    def test_file_exists(self):
        assert SD_TURBO.is_file()

    def test_registers_and_validates(self, sd_turbo):
        assert sd_turbo is not None
        assert sd_turbo.__name__ == "SDTurbo"
        validate_app(sd_turbo)  # raises on a bad structure

    def test_has_generate_endpoint(self, sd_turbo):
        assert sd_turbo.generate._jlserve_endpoint_path == "/generate"

    def test_deploy_settings(self, sd_turbo):
        settings = get_deploy_settings(sd_turbo)
        assert settings.gpu == "L4"
        assert settings.gpus_per_worker == 1
        assert settings.min_workers == 0
        assert settings.max_workers == 1
        assert settings.idle_timeout == 300
        assert settings.weights == ("stabilityai/sd-turbo",)

    def test_declared_weights_match_the_model_loaded_in_setup(self):
        source = SD_TURBO.read_text()
        for w in get_deploy_settings(_load_example(SD_TURBO)).weights:
            assert f'"{w}"' in source, f"{w} declared but not loaded in setup()"

    def test_requirements_extracted_from_file(self):
        reqs = extract_requirements_from_file(str(SD_TURBO))
        assert "diffusers" in reqs
        assert "transformers" in reqs
        assert "accelerate" in reqs

    def test_default_size_is_512(self, sd_turbo):
        input_type = get_method_input_type(sd_turbo.generate)
        data = input_type(prompt="a cat")
        assert (data.width, data.height) == (512, 512)

    @pytest.mark.parametrize("size", [256, 512, 768])
    def test_sizes_within_bounds_accepted(self, sd_turbo, size):
        input_type = get_method_input_type(sd_turbo.generate)
        data = input_type(prompt="a cat", width=size, height=size)
        assert (data.width, data.height) == (size, size)

    @pytest.mark.parametrize("field", ["width", "height"])
    @pytest.mark.parametrize("size", [0, 128, 776, 1024, 4096])
    def test_sizes_outside_bounds_rejected(self, sd_turbo, field, size):
        input_type = get_method_input_type(sd_turbo.generate)
        with pytest.raises(ValidationError):
            input_type(prompt="a cat", **{field: size})

    @pytest.mark.parametrize("field", ["width", "height"])
    def test_size_must_be_multiple_of_8(self, sd_turbo, field):
        input_type = get_method_input_type(sd_turbo.generate)
        with pytest.raises(ValidationError):
            input_type(prompt="a cat", **{field: 500})

    def test_empty_prompt_rejected(self, sd_turbo):
        input_type = get_method_input_type(sd_turbo.generate)
        with pytest.raises(ValidationError):
            input_type(prompt="")
