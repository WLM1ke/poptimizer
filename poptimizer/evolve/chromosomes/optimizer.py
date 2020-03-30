"""Гены и хромосома ответственные за параметры оптимизации."""
from poptimizer.evolve.chromosomes.chromosome import GeneParams, Chromosome

WEIGHT_DECAY = GeneParams(
    path=["optimizer", "weight_decay"],
    default_value=0.01,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=None,
)


class Optimizer(Chromosome):
    """Хромосома ответственная за параметры обучения."""

    _GENES = [WEIGHT_DECAY]
