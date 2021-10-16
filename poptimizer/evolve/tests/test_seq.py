"""Тесты на формулы доверительных интервалов для последовательного тестирования медианы."""
import pytest

from poptimizer.evolve import seq

RADIUS_CASES = (
    (1, 0.05, 1.5774804),
    (60, 0.05, 0.2538789),
    (60, 0.025, 0.2653605),
)


@pytest.mark.parametrize("t, alfa, radius", RADIUS_CASES)
def test_median_conf_radius(t, alfa, radius):
    """Сверка расчетных значений."""
    assert seq._median_conf_radius(t, alfa) == pytest.approx(radius)


ALFA_CASES = (0.05, 0.025)


@pytest.mark.parametrize("alfa", ALFA_CASES)
def test_minimum_n(alfa):
    """Проверка, что радиус меньше 0.5 полученного n, но больше 0.5 для n - 1."""
    n = seq.minimum_bounding_n(alfa)
    assert seq._median_conf_radius(n, alfa, n) < 0.5
    assert seq._median_conf_radius(n - 1, alfa, n - 1) > 0.5


def test_median_conf_bound_small_sample():
    """Ошибка при короткой выборке."""
    with pytest.raises(seq.SmallSampleError):
        seq.median_conf_bound(list(range(11)), 0.025)


def test_median_conf_bound():
    """Проверка ограничения на минимальной выборке и сужения ограничения при ее увеличении."""
    sample = list(range(12))

    lower0, upper0 = seq.median_conf_bound(sample, 0.025)
    assert 0 < lower0 < 1
    assert 10 < upper0 < 11

    sample = sample + sample
    lower1, upper1 = seq.median_conf_bound(sample, 0.025)
    assert lower1 > lower0
    assert upper1 < upper0
