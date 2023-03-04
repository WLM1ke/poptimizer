"""Гены и хромосома ответственные за оптимизацию портфеля."""
from poptimizer.evolve.chromosomes import chromosome

RISK_TOLERANCE = chromosome.GeneParams(
    name="risk_tolerance",
    default_range=(0, 1),
    lower_bound=0,
    upper_bound=1,
    path=("utility", "risk_tolerance"),
    phenotype_function=float,
)


class Utility(chromosome.Chromosome):
    """Хромосома ответственные за оптимизацию портфеля."""

    _genes = (RISK_TOLERANCE,)
