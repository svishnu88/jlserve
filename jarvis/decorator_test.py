"""Unit tests for the app and endpoint decorators."""

import jarvis
from jarvis.decorator import clear_registry, get_endpoint_methods, get_registered_apps


class TestAppDecorator:
    """Tests for the @jarvis.app() class decorator."""

    def test_app_decorator_sets_jarvis_app_flag(self):
        """Test that the decorator sets _jarvis_app on the class."""
        clear_registry()

        @jarvis.app()
        class MyApp:
            pass

        assert hasattr(MyApp, "_jarvis_app")
        assert MyApp._jarvis_app is True

    def test_app_decorator_sets_default_name(self):
        """Test that the decorator sets _jarvis_app_name to class name by default."""
        clear_registry()

        @jarvis.app()
        class MyApp:
            pass

        assert hasattr(MyApp, "_jarvis_app_name")
        assert MyApp._jarvis_app_name == "MyApp"

    def test_app_decorator_with_custom_name(self):
        """Test that the decorator accepts a custom name."""
        clear_registry()

        @jarvis.app(name="CustomName")
        class MyApp:
            pass

        assert MyApp._jarvis_app_name == "CustomName"

    def test_app_decorator_registers_class(self):
        """Test that the decorator registers the class in the registry."""
        clear_registry()

        @jarvis.app()
        class MyApp:
            pass

        registered = get_registered_apps()
        assert len(registered) == 1
        assert registered[0] is MyApp

    def test_multiple_apps_registered(self):
        """Test that multiple apps can be registered."""
        clear_registry()

        @jarvis.app()
        class FirstApp:
            pass

        @jarvis.app()
        class SecondApp:
            pass

        registered = get_registered_apps()
        assert len(registered) == 2
        assert FirstApp in registered
        assert SecondApp in registered

    def test_app_decorator_returns_original_class(self):
        """Test that the decorator returns the original class unchanged."""
        clear_registry()

        @jarvis.app()
        class MyApp:
            def helper(self):
                return "hello"

        instance = MyApp()
        assert instance.helper() == "hello"


class TestEndpointDecorator:
    """Tests for the @jarvis.endpoint() method decorator."""

    def test_endpoint_decorator_sets_flag(self):
        """Test that the decorator sets _jarvis_endpoint on the method."""
        clear_registry()

        @jarvis.app()
        class MyApp:
            @jarvis.endpoint()
            def my_method(self):
                pass

        methods = get_endpoint_methods(MyApp)
        assert len(methods) == 1
        assert methods[0]._jarvis_endpoint is True

    def test_endpoint_decorator_default_path(self):
        """Test that the decorator sets default path from method name."""
        clear_registry()

        @jarvis.app()
        class MyApp:
            @jarvis.endpoint()
            def add(self):
                pass

        methods = get_endpoint_methods(MyApp)
        assert methods[0]._jarvis_endpoint_path == "/add"

    def test_endpoint_decorator_custom_path(self):
        """Test that the decorator accepts a custom path."""
        clear_registry()

        @jarvis.app()
        class MyApp:
            @jarvis.endpoint(path="/custom-path")
            def my_method(self):
                pass

        methods = get_endpoint_methods(MyApp)
        assert methods[0]._jarvis_endpoint_path == "/custom-path"

    def test_multiple_endpoint_methods(self):
        """Test that multiple methods can be decorated as endpoints."""
        clear_registry()

        @jarvis.app()
        class MyApp:
            @jarvis.endpoint()
            def add(self):
                pass

            @jarvis.endpoint()
            def subtract(self):
                pass

            @jarvis.endpoint(path="/mult")
            def multiply(self):
                pass

        methods = get_endpoint_methods(MyApp)
        assert len(methods) == 3

        paths = {m._jarvis_endpoint_path for m in methods}
        assert paths == {"/add", "/subtract", "/mult"}

    def test_endpoint_preserves_method_name(self):
        """Test that functools.wraps preserves method name."""
        clear_registry()

        @jarvis.app()
        class MyApp:
            @jarvis.endpoint()
            def my_endpoint(self):
                pass

        methods = get_endpoint_methods(MyApp)
        assert methods[0].__name__ == "my_endpoint"

    def test_endpoint_preserves_docstring(self):
        """Test that functools.wraps preserves docstring."""
        clear_registry()

        @jarvis.app()
        class MyApp:
            @jarvis.endpoint()
            def my_endpoint(self):
                """This is my docstring."""
                pass

        methods = get_endpoint_methods(MyApp)
        assert methods[0].__doc__ == "This is my docstring."

    def test_non_endpoint_methods_not_included(self):
        """Test that non-decorated methods are not included."""
        clear_registry()

        @jarvis.app()
        class MyApp:
            @jarvis.endpoint()
            def endpoint_method(self):
                pass

            def helper_method(self):
                pass

            def another_helper(self):
                pass

        methods = get_endpoint_methods(MyApp)
        assert len(methods) == 1
        assert methods[0].__name__ == "endpoint_method"


class TestClearRegistry:
    """Tests for the clear_registry function."""

    def test_clear_registry_empties_apps(self):
        """Test that clear_registry empties the app registry."""
        clear_registry()

        @jarvis.app()
        class MyApp:
            pass

        assert len(get_registered_apps()) == 1
        clear_registry()
        assert len(get_registered_apps()) == 0
