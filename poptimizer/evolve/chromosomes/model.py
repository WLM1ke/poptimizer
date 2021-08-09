"""Гены и хромосома ответственные за параметры модели."""
from poptimizer.evolve.chromosomes.chromosome import Chromosome, GeneParams

MODEL_KEY = "model"

START_BN = GeneParams(
    name="start_bn",
    default_range=(-1, 1),
    lower_bound=None,
    upper_bound=None,
    path=(MODEL_KEY, "start_bn"),
    phenotype_function=lambda bn: bn > 0,
)
KERNELS = GeneParams(
    name="kernels",
    default_range=(2, 8),
    lower_bound=1.0,
    upper_bound=None,
    path=(MODEL_KEY, "kernels"),
    phenotype_function=int,
)
SUB_BLOCKS = GeneParams(
    name="sub_blocks",
    default_range=(1, 2),
    lower_bound=1.0,
    upper_bound=None,
    path=(MODEL_KEY, "sub_blocks"),
    phenotype_function=int,
)
GATE_CHANNELS = GeneParams(
    name="gate_channels",
    default_range=(4, 8),
    lower_bound=1.0,
    upper_bound=None,
    path=(MODEL_KEY, "gate_channels"),
    phenotype_function=int,
)
RESIDUAL_CHANNELS = GeneParams(
    name="residual_channels",
    default_range=(4, 8),
    lower_bound=1.0,
    upper_bound=None,
    path=(MODEL_KEY, "residual_channels"),
    phenotype_function=int,
)
SKIP_CHANNELS = GeneParams(
    name="skip_channels",
    default_range=(4, 8),
    lower_bound=1.0,
    upper_bound=None,
    path=(MODEL_KEY, "skip_channels"),
    phenotype_function=int,
)
END_CHANNELS = GeneParams(
    name="end_channels",
    default_range=(4, 8),
    lower_bound=1.0,
    upper_bound=None,
    path=(MODEL_KEY, "end_channels"),
    phenotype_function=int,
)
MIXTURE_SIZE = GeneParams(
    name="mixture_size",
    default_range=(2, 4),
    lower_bound=2.0,
    upper_bound=None,
    path=(MODEL_KEY, "mixture_size"),
    phenotype_function=int,
)


class Model(Chromosome):
    """Хромосома ответственная за параметры модели."""

    _genes = (
        START_BN,
        KERNELS,
        SUB_BLOCKS,
        GATE_CHANNELS,
        RESIDUAL_CHANNELS,
        SKIP_CHANNELS,
        END_CHANNELS,
        MIXTURE_SIZE,
    )
