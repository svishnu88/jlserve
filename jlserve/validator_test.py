"""Unit tests for app and endpoint validation logic."""

import pytest
from pydantic import BaseModel

import jlserve
from jlserve.decorator import _reset_registry
from jlserve.exceptions import EndpointValidationError
from jlserve.validator import (
    get_method_input_type,
    get_method_output_type,
    validate_app,
    validate_has_endpoint_methods,
    validate_is_jlserve_app,
    validate_method_input_is_pydantic_model,
    validate_method_output_is_pydantic_model,
    validate_method_type_hints,
    validate_no_duplicate_paths,
)


class Input(BaseModel):
    value: int


class Output(BaseModel):
    result: int


class TestValidateIsJarvisApp:
    """Tests for validate_is_jlserve_app function."""

    def test_valid_app_class(self):
        _reset_registry()

        @jlserve.app()
        class ValidApp:
            @jlserve.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        validate_is_jlserve_app(ValidApp)

    def test_class_without_app_decorator(self):
        class NotAnApp:
            pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_is_jlserve_app(NotAnApp)
        assert "must be decorated with @jlserve.app()" in str(exc_info.value)


class TestValidateHasEndpointMethods:
    """Tests for validate_has_endpoint_methods function."""

    def test_app_with_endpoints(self):
        _reset_registry()

        @jlserve.app()
        class ValidApp:
            @jlserve.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        validate_has_endpoint_methods(ValidApp)

    def test_app_without_endpoints(self):
        _reset_registry()

        @jlserve.app()
        class EmptyApp:
            def helper(self):
                pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_has_endpoint_methods(EmptyApp)
        assert "must have at least one method decorated with @jlserve.endpoint()" in str(
            exc_info.value
        )


class TestValidateMethodTypeHints:
    """Tests for validate_method_type_hints function."""

    def test_valid_type_hints(self):
        _reset_registry()

        @jlserve.app()
        class ValidApp:
            @jlserve.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        from jlserve.decorator import get_endpoint_methods

        methods = get_endpoint_methods(ValidApp)
        validate_method_type_hints(methods[0])

    def test_missing_input_type_hint(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            @jlserve.endpoint()
            def my_method(self, input) -> Output:
                pass

        from jlserve.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_type_hints(methods[0])
        assert "must have a type hint for input parameter" in str(exc_info.value)

    def test_missing_return_type_hint(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            @jlserve.endpoint()
            def my_method(self, input: Input):
                pass

        from jlserve.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_type_hints(methods[0])
        assert "must have a return type hint" in str(exc_info.value)

    def test_no_input_parameter(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            @jlserve.endpoint()
            def my_method(self) -> Output:
                pass

        from jlserve.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_type_hints(methods[0])
        assert "must accept an input parameter" in str(exc_info.value)


class TestValidateMethodInputIsPydanticModel:
    """Tests for validate_method_input_is_pydantic_model function."""

    def test_valid_pydantic_input(self):
        _reset_registry()

        @jlserve.app()
        class ValidApp:
            @jlserve.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        from jlserve.decorator import get_endpoint_methods

        methods = get_endpoint_methods(ValidApp)
        validate_method_input_is_pydantic_model(methods[0])

    def test_input_is_not_pydantic_model(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            @jlserve.endpoint()
            def my_method(self, input: str) -> Output:
                pass

        from jlserve.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_input_is_pydantic_model(methods[0])
        assert "input type must be a Pydantic BaseModel subclass" in str(exc_info.value)

    def test_input_is_dict(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            @jlserve.endpoint()
            def my_method(self, input: dict) -> Output:
                pass

        from jlserve.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_input_is_pydantic_model(methods[0])
        assert "input type must be a Pydantic BaseModel subclass" in str(exc_info.value)


class TestValidateMethodOutputIsPydanticModel:
    """Tests for validate_method_output_is_pydantic_model function."""

    def test_valid_pydantic_output(self):
        _reset_registry()

        @jlserve.app()
        class ValidApp:
            @jlserve.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        from jlserve.decorator import get_endpoint_methods

        methods = get_endpoint_methods(ValidApp)
        validate_method_output_is_pydantic_model(methods[0])

    def test_output_is_not_pydantic_model(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            @jlserve.endpoint()
            def my_method(self, input: Input) -> str:
                pass

        from jlserve.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_output_is_pydantic_model(methods[0])
        assert "return type must be a Pydantic BaseModel subclass" in str(exc_info.value)

    def test_output_is_dict(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            @jlserve.endpoint()
            def my_method(self, input: Input) -> dict:
                pass

        from jlserve.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_output_is_pydantic_model(methods[0])
        assert "return type must be a Pydantic BaseModel subclass" in str(exc_info.value)


class TestValidateNoDuplicatePaths:
    """Tests for validate_no_duplicate_paths function."""

    def test_unique_paths(self):
        _reset_registry()

        @jlserve.app()
        class ValidApp:
            @jlserve.endpoint()
            def add(self, input: Input) -> Output:
                pass

            @jlserve.endpoint()
            def subtract(self, input: Input) -> Output:
                pass

        validate_no_duplicate_paths(ValidApp)

    def test_duplicate_default_paths(self):
        """This shouldn't happen in practice since method names must be unique."""
        pass  # Method names are unique by Python rules

    def test_duplicate_custom_paths(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            @jlserve.endpoint(path="/same")
            def method1(self, input: Input) -> Output:
                pass

            @jlserve.endpoint(path="/same")
            def method2(self, input: Input) -> Output:
                pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_no_duplicate_paths(InvalidApp)
        assert "Duplicate endpoint path '/same'" in str(exc_info.value)


class TestValidateApp:
    """Tests for the main validate_app function."""

    def test_valid_app(self):
        _reset_registry()

        @jlserve.app()
        class ValidApp:
            def setup(self) -> None:
                pass

            def download_weights(self) -> None:
                pass

            @jlserve.endpoint()
            def add(self, input: Input) -> Output:
                return Output(result=input.value + 1)

            @jlserve.endpoint()
            def subtract(self, input: Input) -> Output:
                return Output(result=input.value - 1)

        validate_app(ValidApp)

    def test_valid_app_with_setup(self):
        _reset_registry()

        @jlserve.app()
        class ValidApp:
            def setup(self):
                self.multiplier = 2

            def download_weights(self) -> None:
                pass

            @jlserve.endpoint()
            def multiply(self, input: Input) -> Output:
                return Output(result=input.value * self.multiplier)

        validate_app(ValidApp)

    def test_invalid_app_not_decorated(self):
        class NotAnApp:
            def method(self, input: Input) -> Output:
                pass

        with pytest.raises(EndpointValidationError):
            validate_app(NotAnApp)

    def test_invalid_app_no_endpoints(self):
        _reset_registry()

        @jlserve.app()
        class EmptyApp:
            pass

        with pytest.raises(EndpointValidationError):
            validate_app(EmptyApp)

    def test_invalid_app_bad_type_hints(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            @jlserve.endpoint()
            def my_method(self, input: str) -> str:
                pass

        with pytest.raises(EndpointValidationError):
            validate_app(InvalidApp)


class TestGetMethodTypes:
    """Tests for get_method_input_type and get_method_output_type functions."""

    def test_get_method_input_type(self):
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        from jlserve.decorator import get_endpoint_methods

        methods = get_endpoint_methods(MyApp)
        assert get_method_input_type(methods[0]) is Input

    def test_get_method_output_type(self):
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        from jlserve.decorator import get_endpoint_methods

        methods = get_endpoint_methods(MyApp)
        assert get_method_output_type(methods[0]) is Output


class TestValidateSetupMethod:
    """Tests for validate_setup_method function."""

    def test_valid_setup_with_none_annotation(self):
        _reset_registry()

        @jlserve.app()
        class ValidApp:
            def setup(self) -> None:
                pass

            def download_weights(self) -> None:
                pass

            @jlserve.endpoint()
            def method(self, input: Input) -> Output:
                pass

        from jlserve.validator import validate_setup_method

        validate_setup_method(ValidApp)

    def test_valid_setup_without_annotation(self):
        _reset_registry()

        @jlserve.app()
        class ValidApp:
            def setup(self):
                pass

            def download_weights(self) -> None:
                pass

            @jlserve.endpoint()
            def method(self, input: Input) -> Output:
                pass

        from jlserve.validator import validate_setup_method

        validate_setup_method(ValidApp)

    def test_missing_setup_method(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            @jlserve.endpoint()
            def method(self, input: Input) -> Output:
                pass

        from jlserve.validator import validate_setup_method

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_setup_method(InvalidApp)
        assert "must define a setup() method" in str(exc_info.value)

    def test_setup_not_callable(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            setup = "not a method"

            @jlserve.endpoint()
            def method(self, input: Input) -> Output:
                pass

        from jlserve.validator import validate_setup_method

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_setup_method(InvalidApp)
        assert "setup must be a method" in str(exc_info.value)

    def test_setup_with_extra_parameters(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            def setup(self, config: dict) -> None:
                pass

            @jlserve.endpoint()
            def method(self, input: Input) -> Output:
                pass

        from jlserve.validator import validate_setup_method

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_setup_method(InvalidApp)
        assert "must only accept 'self'" in str(exc_info.value)
        assert "['self', 'config']" in str(exc_info.value)

    def test_setup_wrong_return_type(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            def setup(self) -> str:
                return "invalid"

            @jlserve.endpoint()
            def method(self, input: Input) -> Output:
                pass

        from jlserve.validator import validate_setup_method

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_setup_method(InvalidApp)
        assert "must return None" in str(exc_info.value)


class TestValidateDownloadWeightsMethod:
    """Tests for validate_download_weights_method function."""

    def test_valid_download_weights_with_none_annotation(self):
        _reset_registry()

        @jlserve.app()
        class ValidApp:
            def setup(self) -> None:
                pass

            def download_weights(self) -> None:
                pass

            @jlserve.endpoint()
            def method(self, input: Input) -> Output:
                pass

        from jlserve.validator import validate_download_weights_method

        validate_download_weights_method(ValidApp)

    def test_valid_download_weights_without_annotation(self):
        _reset_registry()

        @jlserve.app()
        class ValidApp:
            def setup(self) -> None:
                pass

            def download_weights(self):
                pass

            @jlserve.endpoint()
            def method(self, input: Input) -> Output:
                pass

        from jlserve.validator import validate_download_weights_method

        validate_download_weights_method(ValidApp)

    def test_missing_download_weights_method(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            @jlserve.endpoint()
            def method(self, input: Input) -> Output:
                pass

        from jlserve.validator import validate_download_weights_method

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_download_weights_method(InvalidApp)
        assert "must define a download_weights() method" in str(exc_info.value)

    def test_download_weights_not_callable(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            download_weights = "not a method"

            @jlserve.endpoint()
            def method(self, input: Input) -> Output:
                pass

        from jlserve.validator import validate_download_weights_method

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_download_weights_method(InvalidApp)
        assert "download_weights must be a method" in str(exc_info.value)

    def test_download_weights_with_extra_parameters(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            def download_weights(self, cache_dir: str) -> None:
                pass

            @jlserve.endpoint()
            def method(self, input: Input) -> Output:
                pass

        from jlserve.validator import validate_download_weights_method

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_download_weights_method(InvalidApp)
        assert "must only accept 'self'" in str(exc_info.value)
        assert "['self', 'cache_dir']" in str(exc_info.value)

    def test_download_weights_wrong_return_type(self):
        _reset_registry()

        @jlserve.app()
        class InvalidApp:
            def download_weights(self) -> str:
                return "invalid"

            @jlserve.endpoint()
            def method(self, input: Input) -> Output:
                pass

        from jlserve.validator import validate_download_weights_method

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_download_weights_method(InvalidApp)
        assert "must return None" in str(exc_info.value)
