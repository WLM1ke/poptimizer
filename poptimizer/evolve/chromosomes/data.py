"""Гены и хромосома ответственные за параметры данных."""
from poptimizer.evolve.chromosomes.chromosome import GeneParams, Chromosome

BATCH_SIZE = GeneParams(
    name="batch_size",
    default_range=(128.1, 128.9),
    lower_bound=1.0,
    upper_bound=None,
    path=("data", "batch_size"),
    phenotype_function=int,
)
HISTORY_DAYS = GeneParams(
    name="history_days",
    default_range=(50.1, 50.9),
    lower_bound=5,
    upper_bound=None,
    path=("data", "history_days"),
    phenotype_function=int,
)
TICKER_ON = GeneParams(
    name="ticker_on",
    default_range=(0.0, 1.0),
    lower_bound=None,
    upper_bound=None,
    path=("data", "features", "Ticker", "on"),
    phenotype_function=lambda x: x > 0,
)
DAY_OF_YEAR_ON = GeneParams(
    name="day_of_year_on",
    default_range=(0.0, 1.0),
    lower_bound=None,
    upper_bound=None,
    path=("data", "features", "DayOfYear", "on"),
    phenotype_function=lambda x: x > 0,
)
DAY_OF_PERIOD_ON = GeneParams(
    name="day_of_period_on",
    default_range=(-1.0, 0.0),
    lower_bound=None,
    upper_bound=None,
    path=("data", "features", "DayOfPeriod", "on"),
    phenotype_function=lambda x: x > 0,
)
PRICES_ON = GeneParams(
    name="prices_on",
    default_range=(0.0, 1.0),
    lower_bound=None,
    upper_bound=None,
    path=("data", "features", "Prices", "on"),
    phenotype_function=lambda x: x > 0,
)
DIVIDENDS_ON = GeneParams(
    name="dividends_on",
    default_range=(0.0, 1.0),
    lower_bound=None,
    upper_bound=None,
    path=("data", "features", "Dividends", "on"),
    phenotype_function=lambda x: x > 0,
)
TURNOVER_ON = GeneParams(
    name="turnover_on",
    default_range=(0.0, 1.0),
    lower_bound=None,
    upper_bound=None,
    path=("data", "features", "Turnover", "on"),
    phenotype_function=lambda x: x > 0,
)
AVERAGE_TURNOVER_ON = GeneParams(
    name="average_turnover_on",
    default_range=(0.0, 1.0),
    lower_bound=None,
    upper_bound=None,
    path=("data", "features", "AverageTurnover", "on"),
    phenotype_function=lambda x: x > 0,
)
RVI_ON = GeneParams(
    name="rvi_on",
    default_range=(-1.0, 0.0),
    lower_bound=None,
    upper_bound=None,
    path=("data", "features", "RVI", "on"),
    phenotype_function=lambda x: x > 0,
)
MCFTRR_ON = GeneParams(
    name="mcftrr_on",
    default_range=(-1.0, 0.0),
    lower_bound=None,
    upper_bound=None,
    path=("data", "features", "MCFTRR", "on"),
    phenotype_function=lambda x: x > 0,
)
IMOEX_ON = GeneParams(
    name="imoex_on",
    default_range=(-1.0, 0.0),
    lower_bound=None,
    upper_bound=None,
    path=("data", "features", "IMOEX", "on"),
    phenotype_function=lambda x: x > 0,
)
TICKER_TYPE_ON = GeneParams(
    name="ticker_type_on",
    default_range=(-1.0, 0.0),
    lower_bound=None,
    upper_bound=None,
    path=("data", "features", "TickerType", "on"),
    phenotype_function=lambda x: x > 0,
)


class Data(Chromosome):
    """Хромосома ответственная за параметры данных."""

    _GENES = (
        BATCH_SIZE,
        HISTORY_DAYS,
        TICKER_ON,
        DAY_OF_YEAR_ON,
        DAY_OF_PERIOD_ON,
        PRICES_ON,
        DIVIDENDS_ON,
        TURNOVER_ON,
        AVERAGE_TURNOVER_ON,
        RVI_ON,
        MCFTRR_ON,
        IMOEX_ON,
        TICKER_TYPE_ON,
    )
