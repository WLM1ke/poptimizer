from typing import Annotated

from pydantic import PlainSerializer

from poptimizer import consts
from poptimizer.domain.evolve import genetics


class Features(genetics.Chromosome):
    open: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    close: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    high: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    low: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    dividends: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    returns: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    turnover: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    mcftrr: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    meogtrr: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    imoex: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    rvi: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)


class Batch(genetics.Chromosome):
    size: Annotated[
        float,
        genetics.gene_range(lower=1),
        genetics.int_phenotype(),
    ] = genetics.random_default_range(512, 513)
    feats: Features = genetics.random_chromosome(Features)
    history_days: Annotated[
        float,
        genetics.gene_range(lower=2),
        genetics.int_phenotype(),
    ] = genetics.random_default_range(
        consts.INITIAL_HISTORY_DAYS_START,
        consts.INITIAL_HISTORY_DAYS_END,
    )


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
    max_lr: Annotated[
        float,
        genetics.gene_range(lower=0),
    ] = genetics.random_default_range(0.001, 0.01)
    epochs: Annotated[
        float,
        genetics.gene_range(lower=0),
    ] = genetics.random_default_range(1, 2)
    pct_start: Annotated[
        float,
        genetics.gene_range(lower=0, upper=1),
    ] = genetics.random_default_range(0.299, 0.301)
    anneal_strategy: Annotated[
        float,
        PlainSerializer(lambda x: {True: "linear", False: "cos"}[x > 0]),
    ] = genetics.random_default_range(-1, 1)
    cycle_momentum: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)
    base_momentum: Annotated[
        float,
        genetics.gene_range(lower=0, upper=1),
    ] = genetics.random_default_range(0.849, 0.851)
    max_momentum: Annotated[
        float,
        genetics.gene_range(lower=0, upper=1),
    ] = genetics.random_default_range(0.949, 0.951)
    div_factor: Annotated[
        float,
        genetics.gene_range(lower=1),
    ] = genetics.random_default_range(24.9, 25.1)
    final_div_factor: Annotated[
        float,
        genetics.gene_range(lower=1),
    ] = genetics.random_default_range(9999, 10001)
    three_phase: Annotated[
        float,
        genetics.bool_phenotype(),
    ] = genetics.random_default_range(-1, 1)


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
