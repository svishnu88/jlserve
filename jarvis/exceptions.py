"""Custom exception classes for Jarvis SDK."""


class JarvisError(Exception):
    """Base exception for all Jarvis errors."""

    pass


class EndpointValidationError(JarvisError):
    """Raised when an endpoint class fails validation."""

    pass


class EndpointSetupError(JarvisError):
    """Raised when an endpoint's setup() method fails."""

    pass


class MultipleAppsError(JarvisError):
    """Raised when multiple @jarvis.app() classes are defined in a module."""

    pass
