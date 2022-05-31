"""Гены и хромосома ответственные за оптимизацию портфеля."""
from poptimizer.evolve.chromosomes import chromosome

MAX_STD = chromosome.GeneParams(
    name="max_std",
    default_range=(0.1, 0.2),
    lower_bound=0,
    upper_bound=None,
    path=("utility", "max_std"),
    phenotype_function=float,
)


class Utility(chromosome.Chromosome):
    """Хромосома ответственные за оптимизацию портфеля."""

    _genes = (MAX_STD,)
