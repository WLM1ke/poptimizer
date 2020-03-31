"""Гены и хромосома ответственные за политику обучения."""
from poptimizer.evolve.chromosomes import chromosome

MAX_LR = chromosome.GeneParams(
    path=["scheduler", "max_lr"],
    default_value=0.01,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=None,
)
EPOCHS = chromosome.GeneParams(
    path=["scheduler", "epochs"],
    default_value=1.8,
    phenotype_function=int,
    lower_bound=1.0,
    upper_bound=None,
)
PCT_START = chromosome.GeneParams(
    path=["scheduler", "pct_start"],
    default_value=0.3,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=1.0,
)
ANNEAL_STRATEGY = chromosome.GeneParams(
    path=["scheduler", "anneal_strategy"],
    default_value=0.9,
    phenotype_function=lambda x: {0: "cos", 1: "linear"}[int(x)],
    lower_bound=0.0,
    upper_bound=1.99,
)
BASE_MOMENTUM = chromosome.GeneParams(
    path=["scheduler", "base_momentum"],
    default_value=0.85,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=1.0,
)
MAX_MOMENTUM = chromosome.GeneParams(
    path=["scheduler", "max_momentum"],
    default_value=0.95,
    phenotype_function=float,
    lower_bound=0.0,
    upper_bound=1.0,
)
DIV_FACTOR = chromosome.GeneParams(
    path=["scheduler", "div_factor"],
    default_value=25.0,
    phenotype_function=float,
    lower_bound=1.0,
    upper_bound=None,
)
FINAL_DIV_FACTOR = chromosome.GeneParams(
    path=["scheduler", "final_div_factor"],
    default_value=1e4,
    phenotype_function=float,
    lower_bound=1.0,
    upper_bound=None,
)


class Scheduler(chromosome.Chromosome):
    """Хромосома ответственная за параметры One cycle learning rate policy."""

    _GENES = [
        MAX_LR,  # Максимальная скорость обучения
        EPOCHS,  # Количество эпох обучения
        PCT_START,  # Доля шагов разогрева
        ANNEAL_STRATEGY,  # Стратегия снижения скорости обучения
        BASE_MOMENTUM,  # Базовый моментум
        MAX_MOMENTUM,  # Максимальный моментум
        DIV_FACTOR,  # Понижающий коэффициент скорости обучения для периода разогрева
        FINAL_DIV_FACTOR,  # Понижающий коэффициент для скорости обучения в конце цикла понижения
    ]
