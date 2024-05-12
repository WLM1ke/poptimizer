from typing import Any

import pytest

from poptimizer.domain.service import service


class TestComponent: ...


@pytest.mark.parametrize("component", [TestComponent, TestComponent()])
def test_get_component_name(component: Any) -> None:
    assert service.get_component_name(component) == "TestComponent"
