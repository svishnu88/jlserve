"""Custom exception classes for JLServe."""


class JLServeError(Exception):
    """Base exception for all JLServe errors."""

    pass


class EndpointValidationError(JLServeError):
    """Raised when an endpoint class fails validation."""

    pass


class EndpointSetupError(JLServeError):
    """Raised when an endpoint's setup() method fails."""

    pass


class MultipleAppsError(JLServeError):
    """Raised when multiple @jlserve.app() classes are defined in a module."""

    pass


class CacheConfigError(JLServeError):
    """Raised when cache directory configuration is invalid."""

    pass
