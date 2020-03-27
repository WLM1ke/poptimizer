"""Ген ответственный за параметры обучения."""
from poptimizer.evolve.genes.chromosome import GeneParams, Chromosome

MAX_LR = GeneParams(
    path=["scheduler", "max_lr"],
    default_value=0.01,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=None,
)
EPOCHS = GeneParams(
    path=["scheduler", "epochs"],
    default_value=1.3,
    phenotype_function=int,
    lower_bound=1.0,
    upper_bound=None,
)


class Scheduler(Chromosome):
    """Хромосома ответственная за параметры обучения."""

    _GENES = [MAX_LR, EPOCHS]
