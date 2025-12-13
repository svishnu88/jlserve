"""Validation logic for Jarvis endpoint classes."""

import inspect
from typing import Type, get_type_hints

from pydantic import BaseModel

from jarvis.exceptions import EndpointValidationError


def validate_endpoint(cls: Type) -> None:
    """Validate that an endpoint class meets all requirements.

    Args:
        cls: The endpoint class to validate.

    Raises:
        EndpointValidationError: If validation fails.
    """
    validate_has_run_method(cls)
    validate_run_type_hints(cls)
    validate_input_is_pydantic_model(cls)
    validate_output_is_pydantic_model(cls)


def validate_has_run_method(cls: Type) -> None:
    """Check that the class has a run() method.

    Raises:
        EndpointValidationError: If run() method is missing.
    """
    if not hasattr(cls, "run") or not callable(getattr(cls, "run")):
        raise EndpointValidationError(
            "Endpoint class must define a run() method"
        )


def validate_run_type_hints(cls: Type) -> None:
    """Check that run() has type hints for input and return type.

    Raises:
        EndpointValidationError: If type hints are missing.
    """
    run_method = getattr(cls, "run")
    hints = get_type_hints(run_method)

    # Get the signature to check parameter names
    sig = inspect.signature(run_method)
    params = list(sig.parameters.keys())

    # Should have at least 'self' and one input parameter
    if len(params) < 2:
        raise EndpointValidationError(
            "run() must have type hints for input and output"
        )

    # The input parameter (second param after self)
    input_param = params[1]
    if input_param not in hints:
        raise EndpointValidationError(
            "run() must have type hints for input and output"
        )

    # Check return type
    if "return" not in hints:
        raise EndpointValidationError(
            "run() must have type hints for input and output"
        )


def validate_input_is_pydantic_model(cls: Type) -> None:
    """Check that the input type hint is a Pydantic BaseModel subclass.

    Raises:
        EndpointValidationError: If input is not a Pydantic model.
    """
    run_method = getattr(cls, "run")
    hints = get_type_hints(run_method)

    sig = inspect.signature(run_method)
    params = list(sig.parameters.keys())
    input_param = params[1]
    input_type = hints.get(input_param)

    if input_type is None or not _is_pydantic_model(input_type):
        raise EndpointValidationError(
            f"Input type must be a Pydantic BaseModel subclass, got {input_type}"
        )


def validate_output_is_pydantic_model(cls: Type) -> None:
    """Check that the return type hint is a Pydantic BaseModel subclass.

    Raises:
        EndpointValidationError: If output is not a Pydantic model.
    """
    run_method = getattr(cls, "run")
    hints = get_type_hints(run_method)
    output_type = hints.get("return")

    if output_type is None or not _is_pydantic_model(output_type):
        raise EndpointValidationError(
            f"Output type must be a Pydantic BaseModel subclass, got {output_type}"
        )


def _is_pydantic_model(type_hint: Type) -> bool:
    """Check if a type is a Pydantic BaseModel subclass."""
    try:
        return isinstance(type_hint, type) and issubclass(type_hint, BaseModel)
    except TypeError:
        return False


def get_input_type(cls: Type) -> Type[BaseModel]:
    """Get the input Pydantic model type from an endpoint class."""
    run_method = getattr(cls, "run")
    hints = get_type_hints(run_method)
    sig = inspect.signature(run_method)
    params = list(sig.parameters.keys())
    input_param = params[1]
    return hints[input_param]


def get_output_type(cls: Type) -> Type[BaseModel]:
    """Get the output Pydantic model type from an endpoint class."""
    run_method = getattr(cls, "run")
    hints = get_type_hints(run_method)
    return hints["return"]
