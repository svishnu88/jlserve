"""Decorators for defining Jarvis apps and endpoints."""

import functools
from typing import Callable, Optional, Type

from jarvis.exceptions import MultipleAppsError

# Track the single app class for this module
_registered_app: Optional[Type] = None


def app(name: Optional[str] = None):
    """Decorator to mark a class as a Jarvis app.

    The app can contain multiple endpoint methods decorated with @endpoint().

    Only one @jarvis.app() class is allowed per module/deployment. This matches
    ML inference use cases where a single model is loaded per deployment.

    Args:
        name: Optional custom name for the app. Defaults to the class name.

    Returns:
        A decorator function that registers the class as an app.

    Raises:
        MultipleAppsError: If another app class has already been registered.
    """

    def decorator(cls: Type) -> Type:
        global _registered_app

        if _registered_app is not None:
            raise MultipleAppsError(
                f"Only one @jarvis.app() class is allowed per module. "
                f"Found existing app '{_registered_app.__name__}' and attempted to register '{cls.__name__}'. "
                f"For ML inference use cases, deploy each model as a separate app."
            )

        cls._jarvis_app = True
        cls._jarvis_app_name = name if name else cls.__name__
        _registered_app = cls
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


def get_registered_app() -> Optional[Type]:
    """Return the registered app class, or None if no app is registered."""
    return _registered_app


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


def _reset_registry() -> None:
    """Clear the registered app. For testing only."""
    global _registered_app
    _registered_app = None
