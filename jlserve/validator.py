"""Validation logic for JLServe app classes."""

import inspect
from typing import Callable, Type, get_type_hints

from pydantic import BaseModel

from jlserve.decorator import get_endpoint_methods
from jlserve.exceptions import EndpointValidationError


def validate_app(cls: Type, require_download_weights: bool = False) -> None:
    """Validate that an app class meets all requirements.

    Args:
        cls: The app class to validate.
        require_download_weights: If True, validates that the app has a download_weights()
            method with the correct signature. Used by `jlserve build` command.

    Raises:
        EndpointValidationError: If validation fails.
    """
    validate_is_jlserve_app(cls)
    validate_has_endpoint_methods(cls)
    validate_endpoint_methods(cls)
    validate_no_duplicate_paths(cls)
    if require_download_weights:
        validate_download_weights_method(cls)


def validate_is_jlserve_app(cls: Type) -> None:
    """Check that the class is decorated with @jlserve.app().

    Raises:
        EndpointValidationError: If the class is not a JLServe app.
    """
    if not getattr(cls, "_jlserve_app", False):
        raise EndpointValidationError(
            f"Class {cls.__name__} must be decorated with @jlserve.app()"
        )


def validate_has_endpoint_methods(cls: Type) -> None:
    """Check that the app class has at least one @endpoint() decorated method.

    Raises:
        EndpointValidationError: If no endpoint methods are found.
    """
    methods = get_endpoint_methods(cls)
    if not methods:
        raise EndpointValidationError(
            f"App {cls.__name__} must have at least one method decorated with @jlserve.endpoint()"
        )


def validate_endpoint_methods(cls: Type) -> None:
    """Validate all endpoint methods have proper type hints.

    Raises:
        EndpointValidationError: If any endpoint method has invalid type hints.
    """
    methods = get_endpoint_methods(cls)
    for method in methods:
        validate_method_type_hints(method)
        validate_method_input_is_pydantic_model(method)
        validate_method_output_is_pydantic_model(method)


def validate_method_type_hints(method: Callable) -> None:
    """Check that an endpoint method has type hints for input and return type.

    Raises:
        EndpointValidationError: If type hints are missing.
    """
    hints = get_type_hints(method)
    sig = inspect.signature(method)
    params = list(sig.parameters.keys())

    # Should have at least 'self' and one input parameter
    if len(params) < 2:
        raise EndpointValidationError(
            f"Endpoint method {method.__name__}() must accept an input parameter with a type hint"
        )

    # The input parameter (second param after self)
    input_param = params[1]
    if input_param not in hints:
        raise EndpointValidationError(
            f"Endpoint method {method.__name__}() must have a type hint for input parameter '{input_param}'"
        )

    # Check return type
    if "return" not in hints:
        raise EndpointValidationError(
            f"Endpoint method {method.__name__}() must have a return type hint"
        )


def validate_method_input_is_pydantic_model(method: Callable) -> None:
    """Check that the input type hint is a Pydantic BaseModel subclass.

    Raises:
        EndpointValidationError: If input is not a Pydantic model.
    """
    hints = get_type_hints(method)
    sig = inspect.signature(method)
    params = list(sig.parameters.keys())
    input_param = params[1]
    input_type = hints.get(input_param)

    if input_type is None or not _is_pydantic_model(input_type):
        raise EndpointValidationError(
            f"Endpoint method {method.__name__}(): input type must be a Pydantic BaseModel subclass, got {input_type}"
        )


def validate_method_output_is_pydantic_model(method: Callable) -> None:
    """Check that the return type hint is a Pydantic BaseModel subclass.

    Raises:
        EndpointValidationError: If output is not a Pydantic model.
    """
    hints = get_type_hints(method)
    output_type = hints.get("return")

    if output_type is None or not _is_pydantic_model(output_type):
        raise EndpointValidationError(
            f"Endpoint method {method.__name__}(): return type must be a Pydantic BaseModel subclass, got {output_type}"
        )


def validate_no_duplicate_paths(cls: Type) -> None:
    """Check that no two endpoint methods have the same path.

    Raises:
        EndpointValidationError: If duplicate paths are found.
    """
    methods = get_endpoint_methods(cls)
    paths = {}
    for method in methods:
        path = method._jlserve_endpoint_path
        if path in paths:
            raise EndpointValidationError(
                f"Duplicate endpoint path '{path}' found in methods {paths[path]}() and {method.__name__}()"
            )
        paths[path] = method.__name__


def _is_pydantic_model(type_hint: Type) -> bool:
    """Check if a type is a Pydantic BaseModel subclass."""
    try:
        return isinstance(type_hint, type) and issubclass(type_hint, BaseModel)
    except TypeError:
        return False


def get_method_input_type(method: Callable) -> Type[BaseModel]:
    """Get the input Pydantic model type from an endpoint method.

    Args:
        method: The endpoint method to inspect.

    Returns:
        The Pydantic BaseModel subclass used as input type.
    """
    hints = get_type_hints(method)
    sig = inspect.signature(method)
    params = list(sig.parameters.keys())
    input_param = params[1]
    return hints[input_param]


def get_method_output_type(method: Callable) -> Type[BaseModel]:
    """Get the output Pydantic model type from an endpoint method.

    Args:
        method: The endpoint method to inspect.

    Returns:
        The Pydantic BaseModel subclass used as return type.
    """
    hints = get_type_hints(method)
    return hints["return"]
