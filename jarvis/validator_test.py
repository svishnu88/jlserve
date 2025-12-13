"""Unit tests for endpoint validation logic."""

import pytest
from pydantic import BaseModel

from jarvis.exceptions import EndpointValidationError
from jarvis.validator import (
    get_input_type,
    get_output_type,
    validate_endpoint,
    validate_has_run_method,
    validate_input_is_pydantic_model,
    validate_output_is_pydantic_model,
    validate_run_type_hints,
)


class Input(BaseModel):
    name: str


class Output(BaseModel):
    message: str


class TestValidateHasRunMethod:
    def test_valid_class_with_run_method(self):
        class ValidEndpoint:
            def run(self, input: Input) -> Output:
                pass

        validate_has_run_method(ValidEndpoint)

    def test_missing_run_method(self):
        class InvalidEndpoint:
            pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_has_run_method(InvalidEndpoint)
        assert "must define a run() method" in str(exc_info.value)

    def test_run_is_not_callable(self):
        class InvalidEndpoint:
            run = "not a method"

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_has_run_method(InvalidEndpoint)
        assert "must define a run() method" in str(exc_info.value)


class TestValidateRunTypeHints:
    def test_valid_type_hints(self):
        class ValidEndpoint:
            def run(self, input: Input) -> Output:
                pass

        validate_run_type_hints(ValidEndpoint)

    def test_missing_input_type_hint(self):
        class InvalidEndpoint:
            def run(self, input) -> Output:
                pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_run_type_hints(InvalidEndpoint)
        assert "must have type hints for input and output" in str(exc_info.value)

    def test_missing_return_type_hint(self):
        class InvalidEndpoint:
            def run(self, input: Input):
                pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_run_type_hints(InvalidEndpoint)
        assert "must have type hints for input and output" in str(exc_info.value)

    def test_missing_both_type_hints(self):
        class InvalidEndpoint:
            def run(self, input):
                pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_run_type_hints(InvalidEndpoint)
        assert "must have type hints for input and output" in str(exc_info.value)

    def test_no_input_parameter(self):
        class InvalidEndpoint:
            def run(self) -> Output:
                pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_run_type_hints(InvalidEndpoint)
        assert "must have type hints for input and output" in str(exc_info.value)


class TestValidateInputIsPydanticModel:
    def test_valid_pydantic_input(self):
        class ValidEndpoint:
            def run(self, input: Input) -> Output:
                pass

        validate_input_is_pydantic_model(ValidEndpoint)

    def test_input_is_not_pydantic_model(self):
        class InvalidEndpoint:
            def run(self, input: str) -> Output:
                pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_input_is_pydantic_model(InvalidEndpoint)
        assert "Input type must be a Pydantic BaseModel subclass" in str(exc_info.value)

    def test_input_is_dict(self):
        class InvalidEndpoint:
            def run(self, input: dict) -> Output:
                pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_input_is_pydantic_model(InvalidEndpoint)
        assert "Input type must be a Pydantic BaseModel subclass" in str(exc_info.value)


class TestValidateOutputIsPydanticModel:
    def test_valid_pydantic_output(self):
        class ValidEndpoint:
            def run(self, input: Input) -> Output:
                pass

        validate_output_is_pydantic_model(ValidEndpoint)

    def test_output_is_not_pydantic_model(self):
        class InvalidEndpoint:
            def run(self, input: Input) -> str:
                pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_output_is_pydantic_model(InvalidEndpoint)
        assert "Output type must be a Pydantic BaseModel subclass" in str(exc_info.value)

    def test_output_is_dict(self):
        class InvalidEndpoint:
            def run(self, input: Input) -> dict:
                pass

        with pytest.raises(EndpointValidationError) as exc_info:
            validate_output_is_pydantic_model(InvalidEndpoint)
        assert "Output type must be a Pydantic BaseModel subclass" in str(exc_info.value)


class TestValidateEndpoint:
    def test_valid_endpoint(self):
        class ValidEndpoint:
            def run(self, input: Input) -> Output:
                pass

        validate_endpoint(ValidEndpoint)

    def test_valid_endpoint_with_setup(self):
        class ValidEndpoint:
            def setup(self):
                pass

            def run(self, input: Input) -> Output:
                pass

        validate_endpoint(ValidEndpoint)

    def test_invalid_endpoint_no_run(self):
        class InvalidEndpoint:
            pass

        with pytest.raises(EndpointValidationError):
            validate_endpoint(InvalidEndpoint)

    def test_invalid_endpoint_no_type_hints(self):
        class InvalidEndpoint:
            def run(self, input):
                pass

        with pytest.raises(EndpointValidationError):
            validate_endpoint(InvalidEndpoint)


class TestGetInputOutputTypes:
    def test_get_input_type(self):
        class MyEndpoint:
            def run(self, input: Input) -> Output:
                pass

        assert get_input_type(MyEndpoint) is Input

    def test_get_output_type(self):
        class MyEndpoint:
            def run(self, input: Input) -> Output:
                pass

        assert get_output_type(MyEndpoint) is Output
