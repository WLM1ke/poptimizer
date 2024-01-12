from poptimizer.core import domain


class TestComponent:
    ...


def test_get_component_name() -> None:
    assert domain.get_component_name(TestComponent()) == "TestComponent"


def test_get_component_name_for_type() -> None:
    assert domain.get_component_name_for_type(TestComponent) == "TestComponent"
