"""Гены и хромосома ответственные за параметры данных."""
from poptimizer.evolve.chromosomes.chromosome import GeneParams, Chromosome

BATCH_SIZE = GeneParams(
    path=("data", "batch_size"),
    default_range=(128.1, 128.9),
    lower_bound=1.0,
    upper_bound=None,
    phenotype_function=int,
)
HISTORY_DAYS = GeneParams(
    path=("data", "history_days"),
    default_range=(252.1, 252.9),
    lower_bound=2.0,
    upper_bound=None,
    phenotype_function=int,
)
FORECAST_DAYS = GeneParams(
    path=("data", "forecast_days"),
    default_range=(196.1, 196.9),
    lower_bound=1.0,
    upper_bound=None,
    phenotype_function=int,
)
TICKER_ON = GeneParams(
    path=("data", "features", "Ticker", "ticker_on"),
    default_range=(0.0, 1.0),
    lower_bound=None,
    upper_bound=None,
    phenotype_function=lambda x: x > 0,
)


class Data(Chromosome):
    """Хромосома ответственная за параметры данных."""

    _GENES = (BATCH_SIZE, HISTORY_DAYS, FORECAST_DAYS, TICKER_ON)
