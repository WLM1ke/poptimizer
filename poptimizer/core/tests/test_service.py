import pytest

from poptimizer.core import domain


class TestComponent:
    def handler(self) -> None: ...


_CASES = (
    (TestComponent, "TestComponent"),
    (TestComponent(), "TestComponent"),
    (TestComponent().handler, "TestComponent.handler"),
)


@pytest.mark.parametrize(("component", "name"), _CASES)
def test_get_component_name(component, name):
    assert domain.get_component_name(component) == name
