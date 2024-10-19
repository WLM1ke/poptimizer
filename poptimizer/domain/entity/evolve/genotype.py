from typing import Annotated

from poptimizer.domain import consts
from poptimizer.domain.entity.evolve import genetics


class Features(genetics.Chromosome):
    close: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    div: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    ret: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)


class Days(genetics.Chromosome):
    history: Annotated[
        float,
        genetics.gene_range(lower=2),
        genetics.int_phenotype(),
    ] = genetics.random_default_range(
        consts.YEAR_IN_TRADING_DAYS,
        consts.YEAR_IN_TRADING_DAYS + consts.MONTH_IN_TRADING_DAYS,
    )
    forecast: Annotated[
        float,
        genetics.int_phenotype(),
    ] = float(consts.MONTH_IN_TRADING_DAYS)
    test: Annotated[
        float,
        genetics.int_phenotype(),
    ] = float(64)


class Batch(genetics.Chromosome):
    size: Annotated[
        float,
        genetics.gene_range(lower=1),
        genetics.int_phenotype(),
    ] = genetics.random_default_range(128, 128 * 4)
    feats: Features = genetics.random_chromosome(Features)
    days: Days = genetics.random_chromosome(Days)


class Net(genetics.Chromosome):
    use_bn: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    sub_blocks: Annotated[
        float,
        genetics.gene_range(lower=1),
        genetics.int_phenotype(),
    ] = genetics.random_default_range(1, 2)
    kernels: Annotated[
        float,
        genetics.gene_range(lower=1),
        genetics.int_phenotype(),
    ] = genetics.random_default_range(2, 8)
    residual_channels: Annotated[
        float,
        genetics.gene_range(lower=1),
        genetics.int_phenotype(),
    ] = genetics.random_default_range(4, 8)
    gate_channels: Annotated[
        float,
        genetics.gene_range(lower=1),
        genetics.int_phenotype(),
    ] = genetics.random_default_range(4, 8)
    skip_channels: Annotated[
        float,
        genetics.gene_range(lower=1),
        genetics.int_phenotype(),
    ] = genetics.random_default_range(4, 8)
    head_channels: Annotated[
        float,
        genetics.gene_range(lower=1),
        genetics.int_phenotype(),
    ] = genetics.random_default_range(4, 8)
    mixture_size: Annotated[
        float,
        genetics.gene_range(lower=1),
        genetics.int_phenotype(),
    ] = genetics.random_default_range(2, 4)


class Optimizer(genetics.Chromosome): ...


class Scheduler(genetics.Chromosome):
    epochs: Annotated[
        float,
        genetics.gene_range(lower=0),
    ] = genetics.random_default_range(1, 3)
    max_lr: Annotated[
        float,
        genetics.gene_range(lower=0),
    ] = genetics.random_default_range(0.001, 0.01)


class Risk(genetics.Chromosome):
    risk_tolerance: Annotated[
        float,
        genetics.gene_range(lower=0, upper=1),
    ] = genetics.random_default_range(0, 1)


class DLModel(genetics.Chromosome):
    batch: Batch = genetics.random_chromosome(Batch)
    net: Net = genetics.random_chromosome(Net)
    optimizer: Optimizer = genetics.random_chromosome(Optimizer)
    scheduler: Scheduler = genetics.random_chromosome(Scheduler)
    risk: Risk = genetics.random_chromosome(Risk)
