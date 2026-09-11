"""Unit tests for the app and endpoint decorators."""

import pytest

import jlserve
from jlserve.decorator import (
    DeploySettings,
    _reset_registry,
    get_deploy_settings,
    get_endpoint_methods,
    get_registered_app,
)
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


class TestDeploySettings:
    """Tests for the deploy settings accepted by @jlserve.app()."""

    def test_defaults_when_no_deploy_args_given(self):
        _reset_registry()

        @jlserve.app()
        class MyApp:
            pass

        settings = get_deploy_settings(MyApp)
        assert settings.gpu is None
        assert settings.gpus_per_worker == 1
        assert settings.min_workers == 0
        assert settings.max_workers == 1
        assert settings.idle_timeout == 600

    def test_all_settings_are_recorded(self):
        _reset_registry()

        @jlserve.app(
            gpu="H100",
            gpus_per_worker=2,
            min_workers=1,
            max_workers=4,
            idle_timeout=300,
        )
        class MyApp:
            pass

        settings = get_deploy_settings(MyApp)
        assert settings == DeploySettings(
            gpu="H100", gpus_per_worker=2, min_workers=1, max_workers=4, idle_timeout=300
        )

    def test_settings_are_immutable(self):
        _reset_registry()

        @jlserve.app(gpu="L4")
        class MyApp:
            pass

        with pytest.raises(Exception):
            get_deploy_settings(MyApp).gpu = "H100"

    def test_deploy_settings_do_not_affect_requirements_or_name(self):
        _reset_registry()

        @jlserve.app(name="Named", requirements=["torch"], gpu="L4")
        class MyApp:
            pass

        assert MyApp._jlserve_app_name == "Named"
        assert MyApp._jlserve_requirements == ["torch"]
        assert get_deploy_settings(MyApp).gpu == "L4"

    @pytest.mark.parametrize("gpu", ["", "   "])
    def test_empty_gpu_raises(self, gpu):
        _reset_registry()
        with pytest.raises(ValueError, match="gpu must be a non-empty string"):
            @jlserve.app(gpu=gpu)
            class MyApp:
                pass

    def test_non_string_gpu_raises(self):
        _reset_registry()
        with pytest.raises(ValueError, match="gpu must be a non-empty string"):
            @jlserve.app(gpu=4)
            class MyApp:
                pass

    @pytest.mark.parametrize("count", [1, 2, 4, 8])
    def test_allowed_gpus_per_worker(self, count):
        _reset_registry()

        @jlserve.app(gpus_per_worker=count)
        class MyApp:
            pass

        assert get_deploy_settings(MyApp).gpus_per_worker == count

    @pytest.mark.parametrize("count", [0, 3, 5, 16, -1])
    def test_disallowed_gpus_per_worker_raises(self, count):
        _reset_registry()
        with pytest.raises(ValueError, match="gpus_per_worker must be one of"):
            @jlserve.app(gpus_per_worker=count)
            class MyApp:
                pass

    def test_bool_is_not_accepted_as_integer(self):
        _reset_registry()
        with pytest.raises(ValueError, match="gpus_per_worker must be an integer"):
            @jlserve.app(gpus_per_worker=True)
            class MyApp:
                pass

    def test_non_integer_worker_count_raises(self):
        _reset_registry()
        with pytest.raises(ValueError, match="max_workers must be an integer"):
            @jlserve.app(max_workers="2")
            class MyApp:
                pass

    def test_min_greater_than_max_raises(self):
        _reset_registry()
        with pytest.raises(ValueError, match="cannot exceed max_workers"):
            @jlserve.app(min_workers=3, max_workers=2)
            class MyApp:
                pass

    def test_both_worker_counts_zero_raises(self):
        _reset_registry()
        with pytest.raises(ValueError, match="cannot both be 0"):
            @jlserve.app(min_workers=0, max_workers=0)
            class MyApp:
                pass

    def test_min_equal_to_max_is_allowed(self):
        _reset_registry()

        @jlserve.app(min_workers=2, max_workers=2)
        class MyApp:
            pass

        assert get_deploy_settings(MyApp).min_workers == 2

    @pytest.mark.parametrize("field,value", [
        ("min_workers", -1),
        ("min_workers", 101),
        ("max_workers", 101),
    ])
    def test_worker_counts_out_of_range_raise(self, field, value):
        _reset_registry()
        kwargs = {field: value}
        if field == "min_workers" and value > 1:
            kwargs["max_workers"] = value  # keep min <= max so the range check is what fires
        with pytest.raises(ValueError, match=f"{field} must be between 0 and 100"):
            @jlserve.app(**kwargs)
            class MyApp:
                pass

    @pytest.mark.parametrize("value", [-1, 86401])
    def test_idle_timeout_out_of_range_raises(self, value):
        _reset_registry()
        with pytest.raises(ValueError, match="idle_timeout must be between 0 and 86400"):
            @jlserve.app(idle_timeout=value)
            class MyApp:
                pass

    @pytest.mark.parametrize("value", [0, 86400])
    def test_idle_timeout_bounds_are_inclusive(self, value):
        _reset_registry()

        @jlserve.app(idle_timeout=value)
        class MyApp:
            pass

        assert get_deploy_settings(MyApp).idle_timeout == value

    def test_invalid_settings_do_not_register_the_app(self):
        _reset_registry()
        with pytest.raises(ValueError):
            @jlserve.app(gpus_per_worker=3)
            class MyApp:
                pass
        assert get_registered_app() is None


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


class TestWeightsSetting:
    """weights=[...] on @jlserve.app(): Hub ids the platform downloads first."""

    def setup_method(self):
        _reset_registry()

    def teardown_method(self):
        _reset_registry()

    def test_default_is_empty(self):
        @jlserve.app()
        class A:
            pass
        assert get_deploy_settings(A).weights == ()

    def test_recorded_as_tuple_and_stripped(self):
        @jlserve.app(weights=[" stabilityai/sd-turbo ", "black-forest-labs/FLUX.1-schnell"])
        class A:
            pass
        assert get_deploy_settings(A).weights == (
            "stabilityai/sd-turbo", "black-forest-labs/FLUX.1-schnell")

    def test_revision_suffix_allowed(self):
        @jlserve.app(weights=["stabilityai/sd-turbo@fp16"])
        class A:
            pass
        assert get_deploy_settings(A).weights == ("stabilityai/sd-turbo@fp16",)

    @pytest.mark.parametrize("bad", ["sd-turbo", "/x", "a/", "a b/c", "http://x/y", "", 5])
    def test_bad_hub_id_rejected(self, bad):
        with pytest.raises(ValueError, match="weights\\[0\\]"):
            @jlserve.app(weights=[bad])
            class A:
                pass

    def test_must_be_a_list(self):
        with pytest.raises(ValueError, match="weights must be a list"):
            @jlserve.app(weights="stabilityai/sd-turbo")
            class A:
                pass
