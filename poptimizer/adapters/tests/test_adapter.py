import pytest

from poptimizer.adapters import adapter


class TestComponent:
    def handler(self) -> None: ...


_CASES = (
    (TestComponent, "TestComponent"),
    (TestComponent(), "TestComponent"),
    (TestComponent().handler, "TestComponent"),
)


@pytest.mark.parametrize(("component", "name"), _CASES)
def test_get_component_name(component, name):
    assert adapter.get_component_name(component) == name
