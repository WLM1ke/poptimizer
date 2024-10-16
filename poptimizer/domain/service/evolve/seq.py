import functools

import numpy as np
from scipy import special, stats  # type: ignore[reportMissingTypeStubs]


@functools.lru_cache
def _median_conf_radius(
    t: int,
    alfa: float,
    m: int = 1,
    nu: float = 2.04,
    s: float = 1.4,
) -> float:
    """Отклонение выборочной медианы от фактического значения при проведении последовательных тестов.

    Данная функция реализует расчет сужающейся последовательности доверительных интервалов для
    выборочной медианы равномерно корректных по времени тестирования. И базируется на формулах (41) -
    (44), адаптированных для медианы (p=0.5) из работы:

    Sequential estimation of quantiles with applications to A/B-testing and best-arm identification
    https://arxiv.org/abs/1906.09712

    В качестве базовых значений параметров взяты значения из формулы (1). Параметр m отвечает за
    период начала тестирования, а параметры nu и s регулируют форму изменения интервалов по времени и
    могут быть подобраны для минимизации интервала для целевого значения времени t.

    Классические тесты на сравнения двух выборок предполагают выбор до начала эксперимента размеров
    выборок и последующего единственного тестирования гипотезы для заданных размеров выборок.

    Часто до начала эксперимента сложно установить необходимый размер выборки. Однако, если будет
    осуществляться процедура постепенного увеличения выборки и расчета p-value на каждом шаге до
    достижения критического значения, фактическое критическое значение будет существенно завышено. Более
    того закон повторного логарифма гарантирует, что любой уровень значимости из классических тестов
    рано или поздно будет пробит с вероятностью 1.

    При проведении последовательного сравнения так же нельзя воспользоваться классическими методами
    коррекции на множественное тестирования, так как они предполагают слабую зависимость между
    гипотезами. В случае последовательного тестирования гипотеза для момента времени t очень сильно
    связана с гипотезой для момента времени t+1, поэтому обычные корректировки будут слишком
    консервативными.

    :param t:
        Номер интервала для которого осуществляется процедура последовательного тестирования. Тесты
        начинаются с момента времени t >= m и осуществляются последовательно для каждого t.
    :param alfa:
        Значение p-value для процедуры последовательного тестирования. Вероятность пробить
        последовательность доверительных интервалов при тестировании для всех t >= n меньше alfa.
    :param m:
        Период с которого начинается непрерывный анализ выборочной медианы. Должен быть больше или
        равен 1. Значение t >= m.
    :param nu:
        Параметр регулирующий форму убывания радиуса с ростом количества проверок. Должен быть строго
        больше 1. Рекомендуемое значение 2.04 в первой формуле на первой странице.
    :param s:
        Параметр регулирующий форму убывания радиуса с ростом количества проверок. Должен быть строго
        больше 1. Рекомендуемое значение 1.4 в первой формуле на первой странице.
    :return:
        Радиус доверительного интервала для медианы.
    """
    iterated_logarithm = s * np.log(np.log(nu * t / m))
    sequential_probability_ratio = np.log(2 * special.zeta(s) / (alfa * np.log(nu) ** s))  # type: ignore[reportUnknownMemberType]
    l_t = iterated_logarithm + sequential_probability_ratio

    k1 = ((nu**0.25) + (nu**-0.25)) / (2**0.5)

    return k1 * 0.5 * (l_t / t) ** 0.5


@functools.lru_cache
def minimum_bounding_n(alfa: float) -> int:
    n = 1
    while _median_conf_radius(n, alfa, n) >= 1 / 2:
        n += 1

    return n


def median_conf_bound(sample: list[float], p_value: float) -> tuple[float, float]:
    t = len(sample)
    n = minimum_bounding_n(p_value)

    if t < n:
        return -np.inf, np.inf

    radius = _median_conf_radius(t, p_value, n)
    percentiles: tuple[float, float] = tuple(
        stats.scoreatpercentile(  # type: ignore[reportUnknownMemberType]
            sample,
            [(0.5 - radius) * 100, (0.5 + radius) * 100],
        ),
    )

    return percentiles
