"""Unit tests for the app and endpoint decorators."""

import pytest

import jlserve
from jlserve.decorator import _reset_registry, get_endpoint_methods, get_registered_app
from jlserve.exceptions import MultipleAppsError


class TestAppDecorator:
    """Tests for the @jlserve.app() class decorator."""

    def test_app_decorator_sets_jlserve_app_flag(self):
        """Test that the decorator sets _jlserve_app on the class."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            pass

        assert hasattr(MyApp, "_jlserve_app")
        assert MyApp._jlserve_app is True

    def test_app_decorator_sets_default_name(self):
        """Test that the decorator sets _jlserve_app_name to class name by default."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            pass

        assert hasattr(MyApp, "_jlserve_app_name")
        assert MyApp._jlserve_app_name == "MyApp"

    def test_app_decorator_with_custom_name(self):
        """Test that the decorator accepts a custom name."""
        _reset_registry()

        @jlserve.app(name="CustomName")
        class MyApp:
            pass

        assert MyApp._jlserve_app_name == "CustomName"

    def test_app_decorator_registers_class(self):
        """Test that the decorator registers the class."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            pass

        registered = get_registered_app()
        assert registered is MyApp

    def test_multiple_apps_raises_error(self):
        """Test that multiple apps raise MultipleAppsError."""
        _reset_registry()

        @jlserve.app()
        class FirstApp:
            pass

        with pytest.raises(MultipleAppsError) as exc_info:
            @jlserve.app()
            class SecondApp:
                pass

        assert "Only one @jlserve.app()" in str(exc_info.value)
        assert "FirstApp" in str(exc_info.value)
        assert "SecondApp" in str(exc_info.value)

    def test_app_decorator_returns_original_class(self):
        """Test that the decorator returns the original class unchanged."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            def helper(self):
                return "hello"

        instance = MyApp()
        assert instance.helper() == "hello"

    def test_app_decorator_with_requirements(self):
        """Test that the decorator accepts and stores requirements."""
        _reset_registry()

        @jlserve.app(requirements=["torch", "transformers==4.35.0", "numpy>=1.24"])
        class MyApp:
            pass

        assert hasattr(MyApp, "_jlserve_requirements")
        assert MyApp._jlserve_requirements == ["torch", "transformers==4.35.0", "numpy>=1.24"]

    def test_app_decorator_with_empty_requirements(self):
        """Test that the decorator handles empty requirements list."""
        _reset_registry()

        @jlserve.app(requirements=[])
        class MyApp:
            pass

        assert hasattr(MyApp, "_jlserve_requirements")
        assert MyApp._jlserve_requirements == []

    def test_app_decorator_without_requirements(self):
        """Test that the decorator sets empty list when requirements not provided."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            pass

        assert hasattr(MyApp, "_jlserve_requirements")
        assert MyApp._jlserve_requirements == []

    def test_app_decorator_with_various_version_specifiers(self):
        """Test that the decorator accepts various pip version specifier formats."""
        _reset_registry()

        @jlserve.app(
            requirements=[
                "torch",  # No version
                "torch==2.0.0",  # Exact version
                "numpy>=1.24",  # Minimum version
                "pandas<3.0",  # Maximum version
                "flask>=2.0,<3.0",  # Version range
                "torch[cuda]",  # With extras
                "transformers[torch]>=4.30",  # Extras + version
            ]
        )
        class MyApp:
            pass

        assert len(MyApp._jlserve_requirements) == 7
        assert "torch" in MyApp._jlserve_requirements
        assert "transformers[torch]>=4.30" in MyApp._jlserve_requirements

    def test_app_decorator_requirements_not_list_raises_error(self):
        """Test that non-list requirements raises ValueError."""
        _reset_registry()

        with pytest.raises(ValueError) as exc_info:
            @jlserve.app(requirements="torch")
            class MyApp:
                pass

        assert "requirements must be a list" in str(exc_info.value)
        assert "str" in str(exc_info.value)

    def test_app_decorator_requirements_with_non_string_raises_error(self):
        """Test that non-string items in requirements raises ValueError."""
        _reset_registry()

        with pytest.raises(ValueError) as exc_info:
            @jlserve.app(requirements=["torch", 123, "numpy"])
            class MyApp:
                pass

        assert "requirements[1] must be a string" in str(exc_info.value)
        assert "int" in str(exc_info.value)

    def test_app_decorator_requirements_with_empty_string_raises_error(self):
        """Test that empty string in requirements raises ValueError."""
        _reset_registry()

        with pytest.raises(ValueError) as exc_info:
            @jlserve.app(requirements=["torch", "", "numpy"])
            class MyApp:
                pass

        assert "requirements[1] must be a non-empty string" in str(exc_info.value)

    def test_app_decorator_requirements_with_whitespace_only_raises_error(self):
        """Test that whitespace-only string in requirements raises ValueError."""
        _reset_registry()

        with pytest.raises(ValueError) as exc_info:
            @jlserve.app(requirements=["torch", "   ", "numpy"])
            class MyApp:
                pass

        assert "requirements[1] must be a non-empty string" in str(exc_info.value)


class TestEndpointDecorator:
    """Tests for the @jlserve.endpoint() method decorator."""

    def test_endpoint_decorator_sets_flag(self):
        """Test that the decorator sets _jlserve_endpoint on the method."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def my_method(self):
                pass

        methods = get_endpoint_methods(MyApp)
        assert len(methods) == 1
        assert methods[0]._jlserve_endpoint is True

    def test_endpoint_decorator_default_path(self):
        """Test that the decorator sets default path from method name."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def add(self):
                pass

        methods = get_endpoint_methods(MyApp)
        assert methods[0]._jlserve_endpoint_path == "/add"

    def test_endpoint_decorator_custom_path(self):
        """Test that the decorator accepts a custom path."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint(path="/custom-path")
            def my_method(self):
                pass

        methods = get_endpoint_methods(MyApp)
        assert methods[0]._jlserve_endpoint_path == "/custom-path"

    def test_multiple_endpoint_methods(self):
        """Test that multiple methods can be decorated as endpoints."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def add(self):
                pass

            @jlserve.endpoint()
            def subtract(self):
                pass

            @jlserve.endpoint(path="/mult")
            def multiply(self):
                pass

        methods = get_endpoint_methods(MyApp)
        assert len(methods) == 3

        paths = {m._jlserve_endpoint_path for m in methods}
        assert paths == {"/add", "/subtract", "/mult"}

    def test_endpoint_preserves_method_name(self):
        """Test that functools.wraps preserves method name."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def my_endpoint(self):
                pass

        methods = get_endpoint_methods(MyApp)
        assert methods[0].__name__ == "my_endpoint"

    def test_endpoint_preserves_docstring(self):
        """Test that functools.wraps preserves docstring."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def my_endpoint(self):
                """This is my docstring."""
                pass

        methods = get_endpoint_methods(MyApp)
        assert methods[0].__doc__ == "This is my docstring."

    def test_non_endpoint_methods_not_included(self):
        """Test that non-decorated methods are not included."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            @jlserve.endpoint()
            def endpoint_method(self):
                pass

            def helper_method(self):
                pass

            def another_helper(self):
                pass

        methods = get_endpoint_methods(MyApp)
        assert len(methods) == 1
        assert methods[0].__name__ == "endpoint_method"


class TestResetRegistry:
    """Tests for the _reset_registry function."""

    def test_reset_registry_clears_app(self):
        """Test that _reset_registry clears the registered app."""
        _reset_registry()

        @jlserve.app()
        class MyApp:
            pass

        assert get_registered_app() is MyApp
        _reset_registry()
        assert get_registered_app() is None
