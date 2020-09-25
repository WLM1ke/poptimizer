"""Гены и хромосома ответственные за параметры модели."""
from poptimizer.evolve.chromosomes.chromosome import GeneParams, Chromosome

START_BN = GeneParams(
    name="start_bn",
    default_range=(0.0, 1.0),
    lower_bound=None,
    upper_bound=None,
    path=("model", "start_bn"),
    phenotype_function=lambda x: x > 0,
)
KERNELS = GeneParams(
    name="kernels",
    default_range=(2.1, 2.9),
    lower_bound=1.0,
    upper_bound=None,
    path=("model", "kernels"),
    phenotype_function=int,
)
SUB_BLOCKS = GeneParams(
    name="sub_blocks",
    default_range=(1.1, 1.2),
    lower_bound=1.0,
    upper_bound=None,
    path=("model", "sub_blocks"),
    phenotype_function=int,
)
GATE_CHANNELS = GeneParams(
    name="gate_channels",
    default_range=(4.1, 4.9),
    lower_bound=1.0,
    upper_bound=None,
    path=("model", "gate_channels"),
    phenotype_function=int,
)
RESIDUAL_CHANNELS = GeneParams(
    name="residual_channels",
    default_range=(4.1, 4.9),
    lower_bound=1.0,
    upper_bound=None,
    path=("model", "residual_channels"),
    phenotype_function=int,
)
SKIP_CHANNELS = GeneParams(
    name="skip_channels",
    default_range=(4.1, 4.9),
    lower_bound=1.0,
    upper_bound=None,
    path=("model", "skip_channels"),
    phenotype_function=int,
)
END_CHANNELS = GeneParams(
    name="end_channels",
    default_range=(4.1, 4.9),
    lower_bound=1.0,
    upper_bound=None,
    path=("model", "end_channels"),
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
