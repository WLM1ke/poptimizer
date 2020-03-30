"""Гены и хромосома ответственные за параметры модели."""
from poptimizer.evolve.chromosomes.chromosome import GeneParams, Chromosome

START_BN = GeneParams(
    path=["model", "start_bn"],
    default_value=1.2,
    phenotype_function=lambda x: bool(int(x)),
    lower_bound=0.0,
    upper_bound=1.99,
)
KERNELS = GeneParams(
    path=["model", "kernels"],
    default_value=2.3,
    phenotype_function=int,
    lower_bound=1.0,
    upper_bound=None,
)
SUB_BLOCKS = GeneParams(
    path=["model", "sub_blocks"],
    default_value=1.8,
    phenotype_function=int,
    lower_bound=1.0,
    upper_bound=None,
)
GATE_CHANNELS = GeneParams(
    path=["model", "gate_channels"],
    default_value=1.8,
    phenotype_function=int,
    lower_bound=1.0,
    upper_bound=None,
)
RESIDUAL_CHANNELS = GeneParams(
    path=["model", "residual_channels"],
    default_value=1.8,
    phenotype_function=int,
    lower_bound=1.0,
    upper_bound=None,
)
SKIP_CHANNELS = GeneParams(
    path=["model", "skip_channels"],
    default_value=1.8,
    phenotype_function=int,
    lower_bound=1.0,
    upper_bound=None,
)
END_CHANNELS = GeneParams(
    path=["model", "end_channels"],
    default_value=1.8,
    phenotype_function=int,
    lower_bound=1.0,
    upper_bound=None,
)


class Model(Chromosome):
    """Хромосома ответственная за параметры обучения."""

    _GENES = [
        START_BN,
        KERNELS,
        SUB_BLOCKS,
        GATE_CHANNELS,
        RESIDUAL_CHANNELS,
        SKIP_CHANNELS,
        END_CHANNELS,
    ]
