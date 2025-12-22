"""AST-based requirements extraction for JLServe apps.

This module provides functions to extract requirements from Python files
without importing them, solving the chicken-and-egg problem where the file
may have imports that fail if dependencies aren't installed yet.
"""

import ast
from pathlib import Path


def extract_requirements_from_file(file_path: str) -> list[str]:
    """Parse file and extract requirements without importing.

    Args:
        file_path: Path to the Python file containing a @jlserve.app() class.

    Returns:
        List of requirement strings from the requirements parameter.
        Empty list if no requirements found or no @jlserve.app() decorator.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        SyntaxError: If the file contains invalid Python syntax.
    """
    source = Path(file_path).read_text()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for decorator in node.decorator_list:
                if _is_jlserve_app_decorator(decorator):
                    return _extract_requirements_arg(decorator)
    return []


def _is_jlserve_app_decorator(decorator: ast.expr) -> bool:
    """Check if decorator is @jlserve.app or @app.

    Handles both import styles:
    - import jlserve; @jlserve.app(...)
    - from jlserve import app; @app(...)

    Args:
        decorator: AST node representing a decorator.

    Returns:
        True if this is a jlserve.app decorator, False otherwise.
    """
    # Handle @jlserve.app(...) or @jlserve.app
    if isinstance(decorator, ast.Call):
        func = decorator.func
    elif isinstance(decorator, ast.Attribute) or isinstance(decorator, ast.Name):
        # Handle bare @jlserve.app or @app without parens (though our API requires parens)
        func = decorator
    else:
        return False

    # Check for @jlserve.app pattern (ast.Attribute)
    if isinstance(func, ast.Attribute):
        if func.attr == "app":
            # Could be jlserve.app or something_else.app
            # We'll accept any *.app to be permissive
            return True

    # Check for @app pattern (ast.Name)
    if isinstance(func, ast.Name) and func.id == "app":
        return True

    return False


def _extract_requirements_arg(decorator: ast.expr) -> list[str]:
    """Pull out requirements=[...] from decorator.

    Args:
        decorator: AST node representing a @jlserve.app() call.

    Returns:
        List of requirement strings. Empty list if no requirements keyword arg.
    """
    # Only Call nodes have keywords (arguments)
    if not isinstance(decorator, ast.Call):
        return []

    for keyword in decorator.keywords:
        if keyword.arg == "requirements":
            if isinstance(keyword.value, ast.List):
                requirements = []
                for elt in keyword.value.elts:
                    # In Python 3.8+, string literals are ast.Constant
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        requirements.append(elt.value)
                    # Fallback for older Python (ast.Str, deprecated but kept for compatibility)
                    elif hasattr(ast, "Str") and isinstance(elt, ast.Str):
                        requirements.append(elt.s)
                return requirements
    return []
