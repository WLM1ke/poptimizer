"""Гены и хромосома ответственные за параметры данных."""
from poptimizer.evolve.chromosomes.chromosome import GeneParams, Chromosome

BATCH_SIZE = GeneParams(
    path=["data", "batch_size"],
    default_value=100.0,
    phenotype_function=int,
    lower_bound=1.0,
    upper_bound=None,
)
HISTORY_DAYS = GeneParams(
    path=["data", "history_days"],
    default_value=21.0,
    phenotype_function=int,
    lower_bound=1.0,
    upper_bound=None,
)
FORECAST_DAYS = GeneParams(
    path=["data", "forecast_days"],
    default_value=1.8,
    phenotype_function=int,
    lower_bound=1.0,
    upper_bound=None,
)


class Data(Chromosome):
    """Хромосома ответственная за параметры обучения."""

    _GENES = [BATCH_SIZE, HISTORY_DAYS, FORECAST_DAYS]
