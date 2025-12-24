"""Tests for configuration and environment management."""

import os
from pathlib import Path

import pytest

from jlserve.config import get_jlserve_cache_dir
from jlserve.exceptions import CacheConfigError


def test_cache_dir_not_set(monkeypatch):
    """Test that error is raised when JLSERVE_CACHE_DIR is not set."""
    monkeypatch.delenv("JLSERVE_CACHE_DIR", raising=False)

    with pytest.raises(CacheConfigError) as exc_info:
        get_jlserve_cache_dir()

    assert "JLSERVE_CACHE_DIR environment variable must be set" in str(exc_info.value)


def test_cache_dir_does_not_exist(monkeypatch, tmp_path):
    """Test that error is raised when cache directory doesn't exist."""
    non_existent_dir = tmp_path / "does_not_exist"
    monkeypatch.setenv("JLSERVE_CACHE_DIR", str(non_existent_dir))

    with pytest.raises(CacheConfigError) as exc_info:
        get_jlserve_cache_dir()

    assert "directory does not exist" in str(exc_info.value)
    assert str(non_existent_dir) in str(exc_info.value)


def test_cache_dir_is_file_not_directory(monkeypatch, tmp_path):
    """Test that error is raised when JLSERVE_CACHE_DIR points to a file."""
    cache_file = tmp_path / "cache_file.txt"
    cache_file.write_text("not a directory")
    monkeypatch.setenv("JLSERVE_CACHE_DIR", str(cache_file))

    with pytest.raises(CacheConfigError) as exc_info:
        get_jlserve_cache_dir()

    assert "is not a directory" in str(exc_info.value)
    assert str(cache_file) in str(exc_info.value)


def test_cache_dir_valid(monkeypatch, tmp_path):
    """Test that valid cache directory is returned successfully."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setenv("JLSERVE_CACHE_DIR", str(cache_dir))

    result = get_jlserve_cache_dir()

    assert result == cache_dir
    assert isinstance(result, Path)
