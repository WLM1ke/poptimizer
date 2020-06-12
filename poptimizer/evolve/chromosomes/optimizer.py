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
    default_range=(0.999e-8, 1.001e-8),
    lower_bound=0.0,
    upper_bound=None,
    path=("optimizer", "eps"),
    phenotype_function=float,
)
WEIGHT_DECAY = chromosome.GeneParams(
    name="weight_decay",
    default_range=(0.999e-2, 1.01e-2),
    lower_bound=0.0,
    upper_bound=None,
    path=("optimizer", "weight_decay"),
    phenotype_function=float,
)
AMSGRAD = chromosome.GeneParams(
    name="amsgrad",
    default_range=(0.0, 1.0),
    lower_bound=None,
    upper_bound=None,
    path=("optimizer", "amsgrad"),
    phenotype_function=lambda x: x > 0,
)


class Optimizer(chromosome.Chromosome):
    """Хромосома ответственная за параметры оптимизации модели с помощью AdamW."""

    _GENES = (
        BETA2,  # Бета2 - значение Бета1 переписывается One cycle learning rate policy
        EPS,  # Корректировка для численной стабильности
        WEIGHT_DECAY,  # L2 регуляризация
        AMSGRAD,  # Нужно ли использовать AMSGrad
    )
