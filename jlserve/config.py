"""Configuration and environment management for JLServe."""

import os
from pathlib import Path

from jlserve.exceptions import CacheConfigError


def get_jlserve_cache_dir() -> Path:
    """Get and validate JLSERVE_CACHE_DIR from environment.

    Returns:
        Path to cache directory.

    Raises:
        CacheConfigError: If env var not set or directory doesn't exist.
    """
    cache_dir_str = os.getenv("JLSERVE_CACHE_DIR")

    if not cache_dir_str:
        raise CacheConfigError(
            "JLSERVE_CACHE_DIR environment variable must be set. "
            "Set it to a shared directory for caching model weights."
        )

    cache_dir = Path(cache_dir_str)

    if not cache_dir.exists():
        raise CacheConfigError(
            f"JLSERVE_CACHE_DIR directory does not exist: {cache_dir}"
        )

    if not cache_dir.is_dir():
        raise CacheConfigError(
            f"JLSERVE_CACHE_DIR is not a directory: {cache_dir}"
        )

    return cache_dir
