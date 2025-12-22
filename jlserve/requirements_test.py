"""Unit tests for requirements extraction via AST parsing."""

import tempfile
from pathlib import Path

import pytest

from jlserve.requirements import extract_requirements_from_file


class TestExtractRequirementsFromFile:
    """Tests for extract_requirements_from_file function."""

    def test_extract_requirements_with_jlserve_dot_app(self):
        """Test extraction from @jlserve.app(requirements=[...]) pattern."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve

@jlserve.app(requirements=["torch", "transformers==4.35.0", "numpy>=1.24"])
class MyModel:
    pass
""")
            temp_path = f.name

        try:
            requirements = extract_requirements_from_file(temp_path)
            assert requirements == ["torch", "transformers==4.35.0", "numpy>=1.24"]
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_with_bare_app(self):
        """Test extraction from @app(requirements=[...]) pattern."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
from jlserve import app

@app(requirements=["pandas", "scikit-learn>=1.0"])
class MyModel:
    pass
""")
            temp_path = f.name

        try:
            requirements = extract_requirements_from_file(temp_path)
            assert requirements == ["pandas", "scikit-learn>=1.0"]
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_empty_list(self):
        """Test extraction when requirements list is empty."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve

@jlserve.app(requirements=[])
class MyModel:
    pass
""")
            temp_path = f.name

        try:
            requirements = extract_requirements_from_file(temp_path)
            assert requirements == []
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_no_requirements_param(self):
        """Test extraction when no requirements parameter is provided."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve

@jlserve.app()
class MyModel:
    pass
""")
            temp_path = f.name

        try:
            requirements = extract_requirements_from_file(temp_path)
            assert requirements == []
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_no_decorator(self):
        """Test extraction when no @jlserve.app() decorator is present."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
class MyModel:
    pass
""")
            temp_path = f.name

        try:
            requirements = extract_requirements_from_file(temp_path)
            assert requirements == []
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_with_name_and_requirements(self):
        """Test extraction when both name and requirements are specified."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve

@jlserve.app(name="CustomModel", requirements=["torch>=2.0"])
class MyModel:
    pass
""")
            temp_path = f.name

        try:
            requirements = extract_requirements_from_file(temp_path)
            assert requirements == ["torch>=2.0"]
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_with_complex_specifiers(self):
        """Test extraction with various pip version specifier formats."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve

@jlserve.app(requirements=[
    "torch",
    "torch==2.0.0",
    "numpy>=1.24",
    "pandas<3.0",
    "flask>=2.0,<3.0",
    "torch[cuda]",
    "transformers[torch]>=4.30",
])
class MyModel:
    pass
""")
            temp_path = f.name

        try:
            requirements = extract_requirements_from_file(temp_path)
            assert len(requirements) == 7
            assert "torch" in requirements
            assert "torch==2.0.0" in requirements
            assert "torch[cuda]" in requirements
            assert "transformers[torch]>=4.30" in requirements
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_with_failing_imports(self):
        """Test that extraction works even if file has imports that would fail."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import torch  # This would fail if torch not installed
import transformers  # This would fail too

@jlserve.app(requirements=["torch", "transformers"])
class MyModel:
    def predict(self):
        return torch.tensor([1, 2, 3])
""")
            temp_path = f.name

        try:
            # This should NOT fail even if torch/transformers aren't installed
            requirements = extract_requirements_from_file(temp_path)
            assert requirements == ["torch", "transformers"]
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_multiple_classes_first_match(self):
        """Test that extraction returns requirements from first @jlserve.app() class."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve

@jlserve.app(requirements=["torch"])
class FirstModel:
    pass

class SecondModel:
    pass
""")
            temp_path = f.name

        try:
            requirements = extract_requirements_from_file(temp_path)
            assert requirements == ["torch"]
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_with_other_decorators(self):
        """Test extraction when class has multiple decorators."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve

def other_decorator(cls):
    return cls

@other_decorator
@jlserve.app(requirements=["numpy"])
class MyModel:
    pass
""")
            temp_path = f.name

        try:
            requirements = extract_requirements_from_file(temp_path)
            assert requirements == ["numpy"]
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        with pytest.raises(FileNotFoundError):
            extract_requirements_from_file("nonexistent_file.py")

    def test_extract_requirements_invalid_syntax(self):
        """Test that SyntaxError is raised for invalid Python syntax."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("this is not valid python syntax }{[")
            temp_path = f.name

        try:
            with pytest.raises(SyntaxError):
                extract_requirements_from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_multiline_list(self):
        """Test extraction with multiline requirements list."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve

@jlserve.app(
    requirements=[
        "torch",
        "numpy",
        "pandas",
    ]
)
class MyModel:
    pass
""")
            temp_path = f.name

        try:
            requirements = extract_requirements_from_file(temp_path)
            assert requirements == ["torch", "numpy", "pandas"]
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_ignores_non_string_values(self):
        """Test that non-string values in requirements list are ignored."""
        # Note: This would fail at decorator validation time, but AST parsing should handle it
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
import jlserve

@jlserve.app(requirements=["torch", 123, None, "numpy"])
class MyModel:
    pass
""")
            temp_path = f.name

        try:
            requirements = extract_requirements_from_file(temp_path)
            # Should only extract string constants
            assert requirements == ["torch", "numpy"]
        finally:
            Path(temp_path).unlink()

    def test_extract_requirements_with_comments_and_docstrings(self):
        """Test extraction works with comments and docstrings in the file."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("""
# This is a comment
\"\"\"This is a module docstring.\"\"\"

import jlserve

# Another comment
@jlserve.app(requirements=["torch"])  # inline comment
class MyModel:
    \"\"\"Class docstring.\"\"\"
    pass
""")
            temp_path = f.name

        try:
            requirements = extract_requirements_from_file(temp_path)
            assert requirements == ["torch"]
        finally:
            Path(temp_path).unlink()
