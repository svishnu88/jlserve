"""Decorators for defining Jarvis apps and endpoints."""

import functools
from typing import Callable, Optional, Type

# Registry to track all decorated app classes
_app_registry: list[Type] = []


def app(name: Optional[str] = None):
    """Decorator to mark a class as a Jarvis app.

    The app can contain multiple endpoint methods decorated with @endpoint().

    Args:
        name: Optional custom name for the app. Defaults to the class name.

    Returns:
        A decorator function that registers the class as an app.
    """

    def decorator(cls: Type) -> Type:
        cls._jarvis_app = True
        cls._jarvis_app_name = name if name else cls.__name__
        _app_registry.append(cls)
        return cls

    return decorator


def endpoint(path: Optional[str] = None):
    """Decorator to mark a method as a Jarvis endpoint.

    The endpoint path is automatically derived from the method name unless
    a custom path is provided.

    Args:
        path: Optional custom route path. Defaults to "/" + method name.

    Returns:
        A decorator function that marks the method as an endpoint.
    """

    def decorator(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            return method(*args, **kwargs)

        wrapper._jarvis_endpoint = True
        wrapper._jarvis_endpoint_path = path if path else f"/{method.__name__}"
        return wrapper

    return decorator


def get_registered_apps() -> list[Type]:
    """Return all registered app classes."""
    return _app_registry.copy()


def get_endpoint_methods(cls: Type) -> list[Callable]:
    """Retrieve all endpoint-decorated methods from an app class.

    Args:
        cls: The app class to inspect.

    Returns:
        A list of methods that are decorated with @endpoint().
    """
    methods = []
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and getattr(attr, "_jarvis_endpoint", False):
            methods.append(attr)
    return methods


def clear_registry() -> None:
    """Clear the app registry. Useful for testing."""
    _app_registry.clear()
