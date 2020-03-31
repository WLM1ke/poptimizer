"""Гены и хромосома ответственные за параметры оптимизации."""
from poptimizer.evolve.chromosomes import chromosome

BETA2 = chromosome.GeneParams(
    path=["optimizer", "betas"],
    default_value=0.999,
    phenotype_function=lambda x: (0.9, x),
    lower_bound=0.0,
    upper_bound=1.0,
)
EPS = chromosome.GeneParams(
    path=["optimizer", "eps"],
    default_value=1e-8,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=None,
)
WEIGHT_DECAY = chromosome.GeneParams(
    path=["optimizer", "weight_decay"],
    default_value=1e-2,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=None,
)
AMSGRAD = chromosome.GeneParams(
    path=["optimizer", "amsgrad"],
    default_value=0.9,
    phenotype_function=lambda x: bool(int(x)),
    lower_bound=0.0,
    upper_bound=1.99,
)


class Optimizer(chromosome.Chromosome):
    """Хромосома ответственная за параметры оптимизации с помощью AdamW."""

    _GENES = [
        BETA2,  # Бета2 - значение Бета1 переписывается One cycle learning rate policy
        EPS,  # Корректировка для численной стабильности
        WEIGHT_DECAY,  # L2 регуляризация
        AMSGRAD,  # Нужно ли использовать AMSGrad
    ]
