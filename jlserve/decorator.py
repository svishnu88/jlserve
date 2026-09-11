"""Decorators for defining JLServe apps and endpoints."""

import functools
import re
from dataclasses import dataclass
from typing import Callable, Optional, Type

from jlserve.exceptions import MultipleAppsError

# Track the single app class for this module
_registered_app: Optional[Type] = None

# Allowed GPUs per worker. All GPUs of one worker live on one host, so the
# count is bounded by what a single host holds; the platform also requires
# a count that divides evenly for tensor parallelism.
ALLOWED_GPUS_PER_WORKER = (1, 2, 4, 8)
MAX_WORKERS_LIMIT = 100
MAX_IDLE_TIMEOUT_SECONDS = 86400  # 24 hours

# A Hugging Face Hub id: owner/name, optionally @revision. Letters, digits,
# dots, dashes and underscores, as the Hub allows.
_HUB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*(@[A-Za-z0-9._/-]+)?$")


@dataclass(frozen=True)
class DeploySettings:
    """Deploy-time settings declared on @jlserve.app().

    These describe how a deployment should be run once it leaves the local
    machine: which GPU, how many per worker, how many workers, and how long an
    idle worker stays up. They are parsed and validated here; nothing local
    consumes them. A deploy command reads them and hands them to the platform.

    Attributes:
        gpu: GPU type name, e.g. "L4" or "H100". None means "decide at deploy
            time". The platform validates the name against what it offers.
        gpus_per_worker: GPUs attached to one worker. One host, so 1, 2, 4 or 8.
        min_workers: Workers kept warm at all times. 0 means scale to zero.
        max_workers: Upper bound on workers. Must be >= min_workers, and the
            two cannot both be 0.
        idle_timeout: Seconds a worker may sit idle before it is shut down.
        weights: Hugging Face Hub ids the app loads in setup(), e.g.
            ("stabilityai/sd-turbo",). Workers have no internet, so the
            platform downloads these onto the deployment filesystem before the
            worker starts; from_pretrained then finds them in the cache. The
            id also appears inside setup(), the same way a package appears in
            both requirements and an import.
    """

    gpu: Optional[str] = None
    gpus_per_worker: int = 1
    min_workers: int = 0
    max_workers: int = 1
    idle_timeout: int = 600
    weights: tuple[str, ...] = ()


def _validate_deploy_settings(settings: DeploySettings) -> None:
    """Validate deploy settings, raising ValueError with a clear message."""
    if settings.gpu is not None:
        if not isinstance(settings.gpu, str) or not settings.gpu.strip():
            raise ValueError("gpu must be a non-empty string, e.g. 'L4' or 'H100'")

    for name in ("gpus_per_worker", "min_workers", "max_workers", "idle_timeout"):
        value = getattr(settings, name)
        # bool is an int subclass; reject it explicitly so gpus_per_worker=True
        # does not slip through as 1.
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer, got {type(value).__name__}")

    if settings.gpus_per_worker not in ALLOWED_GPUS_PER_WORKER:
        raise ValueError(
            f"gpus_per_worker must be one of {list(ALLOWED_GPUS_PER_WORKER)}, "
            f"got {settings.gpus_per_worker}"
        )

    if not 0 <= settings.min_workers <= MAX_WORKERS_LIMIT:
        raise ValueError(
            f"min_workers must be between 0 and {MAX_WORKERS_LIMIT}, got {settings.min_workers}"
        )
    if not 0 <= settings.max_workers <= MAX_WORKERS_LIMIT:
        raise ValueError(
            f"max_workers must be between 0 and {MAX_WORKERS_LIMIT}, got {settings.max_workers}"
        )
    if settings.min_workers > settings.max_workers:
        raise ValueError(
            f"min_workers ({settings.min_workers}) cannot exceed "
            f"max_workers ({settings.max_workers})"
        )
    if settings.min_workers == 0 and settings.max_workers == 0:
        raise ValueError(
            "min_workers and max_workers cannot both be 0; "
            "a deployment needs capacity for at least one worker"
        )

    if not 0 <= settings.idle_timeout <= MAX_IDLE_TIMEOUT_SECONDS:
        raise ValueError(
            f"idle_timeout must be between 0 and {MAX_IDLE_TIMEOUT_SECONDS} seconds, "
            f"got {settings.idle_timeout}"
        )

    for i, w in enumerate(settings.weights):
        if not isinstance(w, str) or not _HUB_ID.match(w.strip()):
            raise ValueError(
                f"weights[{i}] must be a Hugging Face Hub id like 'owner/name', got {w!r}"
            )


def app(
    name: Optional[str] = None,
    requirements: Optional[list[str]] = None,
    gpu: Optional[str] = None,
    gpus_per_worker: int = 1,
    min_workers: int = 0,
    max_workers: int = 1,
    idle_timeout: int = 600,
    weights: Optional[list[str]] = None,
):
    """Decorator to mark a class as a JLServe app.

    The app can contain multiple endpoint methods decorated with @endpoint().

    Only one @jlserve.app() class is allowed per module/deployment. This matches
    ML inference use cases where a single model is loaded per deployment.

    Args:
        name: Optional custom name for the app. Defaults to the class name.
        requirements: Optional list of Python dependency strings in pip format.
            Each string should be a valid PEP 508 dependency specifier.
            Examples: ["torch", "transformers==4.35.0", "numpy>=1.24"]
        gpu: GPU type to deploy on, e.g. "L4" or "H100". None means decide at
            deploy time. Ignored by `jlserve dev`.
        gpus_per_worker: GPUs attached to one worker: 1, 2, 4 or 8. Ignored by
            `jlserve dev`.
        min_workers: Workers kept warm at all times. 0 scales to zero.
        max_workers: Upper bound on workers. Must be >= min_workers.
        idle_timeout: Seconds an idle worker stays up before shutdown.
        weights: Hugging Face Hub ids the app loads in setup(), e.g.
            ["stabilityai/sd-turbo"]. Downloaded by the platform onto the
            deployment filesystem before the worker starts. Ignored by
            `jlserve dev`, which lets from_pretrained download as usual.

    Returns:
        A decorator function that registers the class as an app.

    Raises:
        MultipleAppsError: If another app class has already been registered.
        ValueError: If requirements or any deploy setting is invalid.
    """

    def decorator(cls: Type) -> Type:
        global _registered_app

        if _registered_app is not None:
            raise MultipleAppsError(
                f"Only one @jlserve.app() class is allowed per module. "
                f"Found existing app '{_registered_app.__name__}' and attempted to register '{cls.__name__}'. "
                f"For ML inference use cases, deploy each model as a separate app."
            )

        # Validate requirements parameter
        if requirements is not None:
            if not isinstance(requirements, list):
                raise ValueError(
                    f"requirements must be a list, got {type(requirements).__name__}"
                )
            for i, req in enumerate(requirements):
                if not isinstance(req, str):
                    raise ValueError(
                        f"requirements[{i}] must be a string, got {type(req).__name__}"
                    )
                if not req.strip():
                    raise ValueError(
                        f"requirements[{i}] must be a non-empty string"
                    )

        if weights is not None and not isinstance(weights, list):
            raise ValueError(f"weights must be a list of Hub ids, got {type(weights).__name__}")

        deploy_settings = DeploySettings(
            gpu=gpu,
            gpus_per_worker=gpus_per_worker,
            min_workers=min_workers,
            max_workers=max_workers,
            idle_timeout=idle_timeout,
            weights=tuple(w.strip() if isinstance(w, str) else w for w in weights) if weights else (),
        )
        _validate_deploy_settings(deploy_settings)

        cls._jlserve_app = True
        cls._jlserve_app_name = name if name else cls.__name__
        cls._jlserve_requirements = requirements if requirements else []
        cls._jlserve_deploy = deploy_settings
        _registered_app = cls
        return cls

    return decorator


def endpoint(path: Optional[str] = None):
    """Decorator to mark a method as a JLServe endpoint.

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

        wrapper._jlserve_endpoint = True
        wrapper._jlserve_endpoint_path = path if path else f"/{method.__name__}"
        return wrapper

    return decorator


def get_registered_app() -> Optional[Type]:
    """Return the registered app class, or None if no app is registered."""
    return _registered_app


def get_deploy_settings(cls: Type) -> DeploySettings:
    """Return the deploy settings declared on an app class.

    Args:
        cls: A class decorated with @jlserve.app().

    Returns:
        The DeploySettings recorded by the decorator. A class decorated without
        any deploy arguments gets the defaults.

    Raises:
        AttributeError: If the class was not decorated with @jlserve.app().
    """
    return cls._jlserve_deploy


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
        if callable(attr) and getattr(attr, "_jlserve_endpoint", False):
            methods.append(attr)
    return methods


def _reset_registry() -> None:
    """Clear the registered app. For testing only."""
    global _registered_app
    _registered_app = None
