from typing import Annotated

from poptimizer import consts
from poptimizer.domain.evolve import genetics


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
        consts.INITIAL_HISTORY_DAYS_START,
        consts.INITIAL_HISTORY_DAYS_END,
    )
    forecast: Annotated[
        float,
        genetics.int_phenotype(),
    ] = float(consts.FORECAST_DAYS)


class Batch(genetics.Chromosome):
    size: Annotated[
        float,
        genetics.gene_range(lower=1),
        genetics.int_phenotype(),
    ] = genetics.random_default_range(512, 513)
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
    ] = genetics.random_default_range(0, 1)
    max_lr: Annotated[
        float,
        genetics.gene_range(lower=0),
    ] = genetics.random_default_range(0.001, 0.01)


class Risk(genetics.Chromosome):
    risk_tolerance: Annotated[
        float,
        genetics.gene_range(lower=0, upper=1),
    ] = genetics.random_default_range(0, 1)


class Genotype(genetics.Chromosome):
    batch: Batch = genetics.random_chromosome(Batch)
    net: Net = genetics.random_chromosome(Net)
    optimizer: Optimizer = genetics.random_chromosome(Optimizer)
    scheduler: Scheduler = genetics.random_chromosome(Scheduler)
    risk: Risk = genetics.random_chromosome(Risk)
