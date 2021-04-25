"""Тесты для базового класса хромосомы."""
import pytest

from poptimizer.evolve.chromosomes import chromosome

BOUND_CASES = (
    (0.1, 0, 1, 0.1),
    (1.1, 0, 1, 0.9),
    (-0.1, 0, 1, 0.1),
    (3.1, 0, 1, 0.9),
    (1.1, None, 1, 0.9),
    (-0.1, 0, None, 0.1),
    (-0.1, None, None, -0.1),
)


@pytest.mark.parametrize("raw, lower, upper, rez", BOUND_CASES)
def test_to_bounds(raw, lower, upper, rez):
    """Тестирование корректности отражения от границ."""
    assert chromosome._to_bounds(raw, lower, upper) == pytest.approx(rez)
