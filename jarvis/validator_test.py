"""Unit tests for app and endpoint validation logic."""

import pytest
from pydantic import BaseModel

import jarvis
from jarvis.decorator import clear_registry
from jarvis.exceptions import EndpointValidationError
from jarvis.validator import (
    get_method_input_type,
    get_method_output_type,
    validate_app,
    validate_has_endpoint_methods,
    validate_is_jarvis_app,
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
    """Tests for validate_is_jarvis_app function."""

    def test_valid_app_class(self):
        clear_registry()

        @jarvis.app()
        class ValidApp:
            @jarvis.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        validate_is_jarvis_app(ValidApp)

    def test_class_without_app_decorator(self):
        class NotAnApp:
            pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_is_jarvis_app(NotAnApp)
        assert "must be decorated with @jarvis.app()" in str(exc_info.value)


class TestValidateHasEndpointMethods:
    """Tests for validate_has_endpoint_methods function."""

    def test_app_with_endpoints(self):
        clear_registry()

        @jarvis.app()
        class ValidApp:
            @jarvis.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        validate_has_endpoint_methods(ValidApp)

    def test_app_without_endpoints(self):
        clear_registry()

        @jarvis.app()
        class EmptyApp:
            def helper(self):
                pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_has_endpoint_methods(EmptyApp)
        assert "must have at least one method decorated with @jarvis.endpoint()" in str(
            exc_info.value
        )


class TestValidateMethodTypeHints:
    """Tests for validate_method_type_hints function."""

    def test_valid_type_hints(self):
        clear_registry()

        @jarvis.app()
        class ValidApp:
            @jarvis.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        from jarvis.decorator import get_endpoint_methods

        methods = get_endpoint_methods(ValidApp)
        validate_method_type_hints(methods[0])

    def test_missing_input_type_hint(self):
        clear_registry()

        @jarvis.app()
        class InvalidApp:
            @jarvis.endpoint()
            def my_method(self, input) -> Output:
                pass

        from jarvis.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_type_hints(methods[0])
        assert "must have a type hint for input parameter" in str(exc_info.value)

    def test_missing_return_type_hint(self):
        clear_registry()

        @jarvis.app()
        class InvalidApp:
            @jarvis.endpoint()
            def my_method(self, input: Input):
                pass

        from jarvis.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_type_hints(methods[0])
        assert "must have a return type hint" in str(exc_info.value)

    def test_no_input_parameter(self):
        clear_registry()

        @jarvis.app()
        class InvalidApp:
            @jarvis.endpoint()
            def my_method(self) -> Output:
                pass

        from jarvis.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_type_hints(methods[0])
        assert "must accept an input parameter" in str(exc_info.value)


class TestValidateMethodInputIsPydanticModel:
    """Tests for validate_method_input_is_pydantic_model function."""

    def test_valid_pydantic_input(self):
        clear_registry()

        @jarvis.app()
        class ValidApp:
            @jarvis.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        from jarvis.decorator import get_endpoint_methods

        methods = get_endpoint_methods(ValidApp)
        validate_method_input_is_pydantic_model(methods[0])

    def test_input_is_not_pydantic_model(self):
        clear_registry()

        @jarvis.app()
        class InvalidApp:
            @jarvis.endpoint()
            def my_method(self, input: str) -> Output:
                pass

        from jarvis.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_input_is_pydantic_model(methods[0])
        assert "input type must be a Pydantic BaseModel subclass" in str(exc_info.value)

    def test_input_is_dict(self):
        clear_registry()

        @jarvis.app()
        class InvalidApp:
            @jarvis.endpoint()
            def my_method(self, input: dict) -> Output:
                pass

        from jarvis.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_input_is_pydantic_model(methods[0])
        assert "input type must be a Pydantic BaseModel subclass" in str(exc_info.value)


class TestValidateMethodOutputIsPydanticModel:
    """Tests for validate_method_output_is_pydantic_model function."""

    def test_valid_pydantic_output(self):
        clear_registry()

        @jarvis.app()
        class ValidApp:
            @jarvis.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        from jarvis.decorator import get_endpoint_methods

        methods = get_endpoint_methods(ValidApp)
        validate_method_output_is_pydantic_model(methods[0])

    def test_output_is_not_pydantic_model(self):
        clear_registry()

        @jarvis.app()
        class InvalidApp:
            @jarvis.endpoint()
            def my_method(self, input: Input) -> str:
                pass

        from jarvis.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_output_is_pydantic_model(methods[0])
        assert "return type must be a Pydantic BaseModel subclass" in str(exc_info.value)

    def test_output_is_dict(self):
        clear_registry()

        @jarvis.app()
        class InvalidApp:
            @jarvis.endpoint()
            def my_method(self, input: Input) -> dict:
                pass

        from jarvis.decorator import get_endpoint_methods

        methods = get_endpoint_methods(InvalidApp)
        with pytest.raises(EndpointValidationError) as exc_info:
            validate_method_output_is_pydantic_model(methods[0])
        assert "return type must be a Pydantic BaseModel subclass" in str(exc_info.value)


class TestValidateNoDuplicatePaths:
    """Tests for validate_no_duplicate_paths function."""

    def test_unique_paths(self):
        clear_registry()

        @jarvis.app()
        class ValidApp:
            @jarvis.endpoint()
            def add(self, input: Input) -> Output:
                pass

            @jarvis.endpoint()
            def subtract(self, input: Input) -> Output:
                pass

        validate_no_duplicate_paths(ValidApp)

    def test_duplicate_default_paths(self):
        """This shouldn't happen in practice since method names must be unique."""
        pass  # Method names are unique by Python rules

    def test_duplicate_custom_paths(self):
        clear_registry()

        @jarvis.app()
        class InvalidApp:
            @jarvis.endpoint(path="/same")
            def method1(self, input: Input) -> Output:
                pass

            @jarvis.endpoint(path="/same")
            def method2(self, input: Input) -> Output:
                pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_no_duplicate_paths(InvalidApp)
        assert "Duplicate endpoint path '/same'" in str(exc_info.value)


class TestValidateApp:
    """Tests for the main validate_app function."""

    def test_valid_app(self):
        clear_registry()

        @jarvis.app()
        class ValidApp:
            @jarvis.endpoint()
            def add(self, input: Input) -> Output:
                return Output(result=input.value + 1)

            @jarvis.endpoint()
            def subtract(self, input: Input) -> Output:
                return Output(result=input.value - 1)

        validate_app(ValidApp)

    def test_valid_app_with_setup(self):
        clear_registry()

        @jarvis.app()
        class ValidApp:
            def setup(self):
                self.multiplier = 2

            @jarvis.endpoint()
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
        clear_registry()

        @jarvis.app()
        class EmptyApp:
            pass

        with pytest.raises(EndpointValidationError):
            validate_app(EmptyApp)

    def test_invalid_app_bad_type_hints(self):
        clear_registry()

        @jarvis.app()
        class InvalidApp:
            @jarvis.endpoint()
            def my_method(self, input: str) -> str:
                pass

        with pytest.raises(EndpointValidationError):
            validate_app(InvalidApp)


class TestGetMethodTypes:
    """Tests for get_method_input_type and get_method_output_type functions."""

    def test_get_method_input_type(self):
        clear_registry()

        @jarvis.app()
        class MyApp:
            @jarvis.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        from jarvis.decorator import get_endpoint_methods

        methods = get_endpoint_methods(MyApp)
        assert get_method_input_type(methods[0]) is Input

    def test_get_method_output_type(self):
        clear_registry()

        @jarvis.app()
        class MyApp:
            @jarvis.endpoint()
            def my_method(self, input: Input) -> Output:
                pass

        from jarvis.decorator import get_endpoint_methods

        methods = get_endpoint_methods(MyApp)
        assert get_method_output_type(methods[0]) is Output
