"""Decorator for defining Jarvis endpoints."""

from typing import Type

# Registry to track all decorated endpoint classes
_endpoint_registry: list[Type] = []


def endpoint():
    """Decorator to mark a class as a Jarvis endpoint.

    The endpoint name is automatically derived from the class name.

    Returns:
        A decorator function that registers the class as an endpoint.
    """

    def decorator(cls: Type) -> Type:
        cls._jarvis_endpoint_name = cls.__name__
        _endpoint_registry.append(cls)
        return cls

    return decorator


def get_registered_endpoints() -> list[Type]:
    """Return all registered endpoint classes."""
    return _endpoint_registry.copy()


def clear_registry() -> None:
    """Clear the endpoint registry. Useful for testing."""
    _endpoint_registry.clear()
