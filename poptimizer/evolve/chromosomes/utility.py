"""Гены и хромосома ответственные за оптимизацию портфеля."""
from poptimizer.evolve.chromosomes import chromosome

RISK_AVERSION = chromosome.GeneParams(
    name="risk_aversion",
    default_range=(0, 1),
    lower_bound=0,
    upper_bound=None,
    path=("utility", "risk_aversion"),
    phenotype_function=float,
)

ERROR_TOLERANCE = chromosome.GeneParams(
    name="error_tolerance",
    default_range=(0, 1),
    lower_bound=0,
    upper_bound=None,
    path=("utility", "error_tolerance"),
    phenotype_function=float,
)


class Utility(chromosome.Chromosome):
    """Хромосома ответственные за параметры функции полезности при оптимизации портфеля.

    Оптимизация портфеля осуществляется с использованием функции полезности следующего вида:

    U = r - risk_aversion / 2 * s ** 2 - error_tolerance * s, где

    risk_aversion - классическая нелюбовь к риску в задачах mean-variance оптимизации. При значении 1 в первом
    приближении максимизируется логарифм доходности или ожидаемые темпы роста портфеля.

    error_tolerance - величина минимальной требуемой величины коэффициента Шарпа или мера возможной достоверности оценок
    доходности. В рамках второй интерпретации происходит максимизация нижней границы доверительного интервала.
    """

    _genes = (
        RISK_AVERSION,
        ERROR_TOLERANCE,
    )
