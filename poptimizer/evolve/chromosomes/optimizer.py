"""Гены и хромосома ответственные за параметры оптимизации модели."""
from poptimizer.evolve.chromosomes import chromosome

BETA2 = chromosome.GeneParams(
    name="betas",
    default_range=(0.99899, 0.99901),
    lower_bound=0.0,
    upper_bound=1.0,
    path=("optimizer", "betas"),
    phenotype_function=lambda x: (0.9, x),
)
EPS = chromosome.GeneParams(
    name="eps",
    default_range=(1.0e-9, 1.0e-7),
    lower_bound=0.0,
    upper_bound=None,
    path=("optimizer", "eps"),
    phenotype_function=float,
)
WEIGHT_DECAY = chromosome.GeneParams(
    name="weight_decay",
    default_range=(1.0e-3, 1.0e-1),
    lower_bound=0.0,
    upper_bound=None,
    path=("optimizer", "weight_decay"),
    phenotype_function=float,
)


class Optimizer(chromosome.Chromosome):
    """Хромосома ответственная за параметры оптимизации модели с помощью AdamW."""

    _genes = (
        BETA2,  # Бета2 - значение Бета1 переписывается One cycle learning rate policy
        EPS,  # Корректировка для численной стабильности
        WEIGHT_DECAY,  # L2 регуляризация
    )
