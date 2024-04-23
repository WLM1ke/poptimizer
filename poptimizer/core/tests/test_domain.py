from typing import Any

import pytest

from poptimizer.core import domain


class TestComponent: ...


@pytest.mark.parametrize("component", [TestComponent, TestComponent()])
def test_get_component_name(component: Any) -> None:
    assert domain.get_component_name(component) == "TestComponent"
