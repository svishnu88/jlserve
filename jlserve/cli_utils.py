"""Shared utilities for CLI commands.

This module provides reusable helper functions for the dev and build commands.
It was extracted from cli.py to follow the DRY (Don't Repeat Yourself) principle,
centralizing common logic for:

- File validation (ensuring files exist and are Python files)
- Requirements extraction and installation (using AST parsing + uv)
- App loading (dynamic import and registry retrieval)

These utilities handle the core workflow that both commands share:
1. Validate the input file
2. Extract and install requirements (without importing)
3. Dynamically load the file and get the @jlserve.app() class
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Type

import typer

from jlserve.decorator import _reset_registry, get_registered_app
from jlserve.requirements import extract_requirements_from_file


def validate_python_file(file: Path) -> None:
    """Validate that file exists and is a Python file.

    Args:
        file: Path to validate.

    Raises:
        typer.Exit: If validation fails.
    """
    if not file.exists():
        typer.echo(f"Error: File not found: {file}", err=True)
        raise typer.Exit(1)

    if not file.suffix == ".py":
        typer.echo(f"Error: File must be a Python file: {file}", err=True)
        raise typer.Exit(1)


def install_requirements(file: Path, cache_dir: Path) -> None:
    """Extract and install requirements from a Python file.

    This function solves the chicken-and-egg problem: we need to install packages
    before importing the file, but the requirements are specified inside the file.
    Solution: use AST parsing to extract requirements without executing the code.

    UV will use the cache_dir for caching downloaded packages, ensuring fast
    reinstalls across container restarts.

    Args:
        file: Python file to extract requirements from.
        cache_dir: Directory to use for UV package cache (UV_CACHE_DIR).

    Raises:
        typer.Exit: If extraction or installation fails.
    """
    # Extract requirements via AST (parse without executing)
    # This reads @jlserve.app(requirements=[...]) without importing
    try:
        requirements = extract_requirements_from_file(str(file))
    except SyntaxError as e:
        typer.echo(f"Error: Invalid Python syntax in {file}: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: Failed to extract requirements from {file}: {e}", err=True)
        raise typer.Exit(1)

    # Install requirements using uv (fast, skips if already installed)
    if requirements:
        typer.echo(f"Installing requirements: {', '.join(requirements)}")
        try:
            # Set UV_CACHE_DIR to use JLSERVE_CACHE_DIR for package caching
            # This ensures packages are cached in persistent storage
            env = os.environ.copy()
            env["UV_CACHE_DIR"] = str(cache_dir)

            subprocess.run(
                ["uv", "pip", "install", *requirements],
                check=True,
                env=env,
            )
        except subprocess.CalledProcessError as e:
            typer.echo(f"Error: Failed to install requirements: {e}", err=True)
            raise typer.Exit(1)
        except FileNotFoundError:
            typer.echo(
                "Error: 'uv' command not found. Please install uv: https://github.com/astral-sh/uv",
                err=True,
            )
            raise typer.Exit(1)


def load_app_class(file: Path) -> Type:
    """Load a Python file and return the registered app class.

    Uses dynamic import to load the user's Python file and retrieve the
    @jlserve.app() decorated class from the global registry.

    Args:
        file: Python file containing a @jlserve.app() class.

    Returns:
        The registered app class.

    Raises:
        typer.Exit: If loading fails or no app is found.
    """
    # Clear any previously registered app from the global registry
    # This ensures we only get the app from the current file
    _reset_registry()

    # Dynamically import the user's Python file
    spec = importlib.util.spec_from_file_location("user_module", file)
    if spec is None or spec.loader is None:
        typer.echo(f"Error: Could not load file: {file}", err=True)
        raise typer.Exit(1)

    # Create module and register in sys.modules
    module = importlib.util.module_from_spec(spec)
    sys.modules["user_module"] = module

    # Execute the module (this triggers @jlserve.app() decorator registration)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        # Check if it's a MultipleAppsError (only one @jlserve.app() allowed)
        if "MultipleAppsError" in type(e).__name__ or "multiple" in str(e).lower():
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
        # Re-raise other exceptions (import errors, syntax errors, etc.)
        raise

    # Retrieve the app class from the global registry
    app_cls = get_registered_app()
    if app_cls is None:
        typer.echo(
            "Error: No app found. Did you decorate a class with @jlserve.app()?",
            err=True,
        )
        raise typer.Exit(1)

    return app_cls
