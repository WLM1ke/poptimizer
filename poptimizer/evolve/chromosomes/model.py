"""Гены и хромосома ответственные за параметры модели."""
from poptimizer.evolve.chromosomes.chromosome import GeneParams, Chromosome

START_BN = GeneParams(
    path=("model", "start_bn"),
    default_range=(1.1, 1.2),
    lower_bound=0.0,
    upper_bound=1.99,
    phenotype_function=lambda x: bool(int(x)),
)
KERNELS = GeneParams(
    path=("model", "kernels"),
    default_range=(2.1, 2.9),
    lower_bound=1.0,
    upper_bound=None,
    phenotype_function=int,
)
SUB_BLOCKS = GeneParams(
    path=("model", "sub_blocks"),
    default_range=(1.1, 1.2),
    lower_bound=1.0,
    upper_bound=None,
    phenotype_function=int,
)
GATE_CHANNELS = GeneParams(
    path=("model", "gate_channels"),
    default_range=(4.1, 4.9),
    lower_bound=1.0,
    upper_bound=None,
    phenotype_function=int,
)
RESIDUAL_CHANNELS = GeneParams(
    path=("model", "residual_channels"),
    default_range=(4.1, 4.9),
    lower_bound=1.0,
    upper_bound=None,
    phenotype_function=int,
)
SKIP_CHANNELS = GeneParams(
    path=("model", "skip_channels"),
    default_range=(4.1, 4.9),
    lower_bound=1.0,
    upper_bound=None,
    phenotype_function=int,
)
END_CHANNELS = GeneParams(
    path=("model", "end_channels"),
    default_range=(4.1, 4.9),
    lower_bound=1.0,
    upper_bound=None,
    phenotype_function=int,
)


class Model(Chromosome):
    """Хромосома ответственная за параметры модели."""

    _GENES = (
        START_BN,
        KERNELS,
        SUB_BLOCKS,
        GATE_CHANNELS,
        RESIDUAL_CHANNELS,
        SKIP_CHANNELS,
        END_CHANNELS,
    )
