from typing import Any

import pytest

from poptimizer.adapter import adapter


class TestComponent: ...


@pytest.mark.parametrize("component", [TestComponent, TestComponent()])
def test_get_component_name(component: Any) -> None:
    assert adapter.get_component_name(component) == "TestComponent"
