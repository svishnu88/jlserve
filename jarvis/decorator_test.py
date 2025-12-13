"""Unit tests for the endpoint decorator."""

import jarvis
from jarvis.decorator import clear_registry, get_registered_endpoints


def test_endpoint_decorator_sets_name():
    """Test that the decorator sets _jarvis_endpoint_name on the class."""
    clear_registry()

    @jarvis.endpoint()
    class MyEndpoint:
        pass

    assert hasattr(MyEndpoint, "_jarvis_endpoint_name")
    assert MyEndpoint._jarvis_endpoint_name == "MyEndpoint"


def test_endpoint_decorator_registers_class():
    """Test that the decorator registers the class in the registry."""
    clear_registry()

    @jarvis.endpoint()
    class MyEndpoint:
        pass

    registered = get_registered_endpoints()
    assert len(registered) == 1
    assert registered[0] is MyEndpoint


def test_multiple_endpoints_registered():
    """Test that multiple endpoints can be registered."""
    clear_registry()

    @jarvis.endpoint()
    class FirstEndpoint:
        pass

    @jarvis.endpoint()
    class SecondEndpoint:
        pass

    registered = get_registered_endpoints()
    assert len(registered) == 2
    assert FirstEndpoint in registered
    assert SecondEndpoint in registered


def test_decorator_returns_original_class():
    """Test that the decorator returns the original class unchanged."""
    clear_registry()

    @jarvis.endpoint()
    class MyEndpoint:
        def run(self):
            return "hello"

    instance = MyEndpoint()
    assert instance.run() == "hello"


def test_clear_registry():
    """Test that clear_registry empties the registry."""
    clear_registry()

    @jarvis.endpoint()
    class MyEndpoint:
        pass

    assert len(get_registered_endpoints()) == 1
    clear_registry()
    assert len(get_registered_endpoints()) == 0
