"""Гены и хромосома ответственные за параметры обучения."""
from poptimizer.evolve.chromosomes.chromosome import GeneParams, Chromosome

MAX_LR = GeneParams(
    path=["scheduler", "max_lr"],
    default_value=0.01,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=None,
)
EPOCHS = GeneParams(
    path=["scheduler", "epochs"],
    default_value=1.8,
    phenotype_function=int,
    lower_bound=1.0,
    upper_bound=None,
)
PCT_START = GeneParams(
    path=["scheduler", "pct_start"],
    default_value=0.3,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=1.0,
)
ANNEAL_STRATEGY = GeneParams(
    path=["scheduler", "anneal_strategy"],
    default_value=0.8,
    phenotype_function=lambda x: {0: "cos", 1: "liner"}[int(x)],
    lower_bound=0.0,
    upper_bound=1.99,
)
CYCLE_MOMENTUM = GeneParams(
    path=["scheduler", "cycle_momentum"],
    default_value=1.2,
    phenotype_function=lambda x: bool(int(x)),
    lower_bound=0.0,
    upper_bound=1.99,
)
BASE_MOMENTUM = GeneParams(
    path=["scheduler", "base_momentum"],
    default_value=0.85,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=1.0,
)
MAX_MOMENTUM = GeneParams(
    path=["scheduler", "max_momentum"],
    default_value=0.95,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=1.0,
)
DIV_FACTOR = GeneParams(
    path=["scheduler", "div_factor"],
    default_value=25.0,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=None,
)
FINAL_DIV_FACTOR = GeneParams(
    path=["scheduler", "final_div_factor"],
    default_value=1e4,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=None,
)


class Scheduler(Chromosome):
    """Хромосома ответственная за параметры обучения."""

    _GENES = [
        MAX_LR,
        EPOCHS,
        PCT_START,
        ANNEAL_STRATEGY,
        CYCLE_MOMENTUM,
        BASE_MOMENTUM,
        MAX_MOMENTUM,
        DIV_FACTOR,
        FINAL_DIV_FACTOR,
    ]
