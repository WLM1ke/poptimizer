from __future__ import annotations

import functools
import itertools
import random
from typing import Annotated, Any, Self

import bson
from pydantic import AfterValidator, BaseModel, Field, PlainSerializer, computed_field, field_validator, model_validator

from poptimizer.core import domain, errors

type Genes = dict[str, float | Genes]


class Chromosome(BaseModel):
    @property
    def phenotype(self) -> dict[str, Any]:
        return self.model_dump()

    @property
    def genes(self) -> Genes:
        base_genes = dict(self)

        genes: Genes = {}

        for gene, value in base_genes.items():
            match value:
                case float():
                    genes[gene] = value
                case Chromosome():
                    genes[gene] = value.genes
                case _:
                    raise errors.DomainError(f"unknown gene type {type(value)}")

        return genes

    def make_child(self, parent1: Self, parent2: Self, scale: float) -> Self:
        genes = dict(self)
        genes1 = dict(parent1)
        genes2 = dict(parent2)

        child = {}

        for gene, value in genes.items():
            match value:
                case float():
                    child[gene] = value + (genes1[gene] - genes2[gene]) * scale * random.gauss()
                case Chromosome():
                    child[gene] = value.make_child(genes1[gene], genes2[gene], scale)
                case _:
                    raise errors.DomainError(f"unknown gene type {type(value)}")

        return self.model_validate(child)


def _range_validator_wrapper(value: float, lower: float | None, upper: float | None) -> float:
    if lower is not None and value < lower:
        return _range_validator_wrapper(lower + (lower - value), lower, upper)

    if upper is not None and value > upper:
        return _range_validator_wrapper(upper - (value - upper), lower, upper)

    return value


def gene_range(lower: float | None = None, upper: float | None = None) -> AfterValidator:
    return AfterValidator(functools.partial(_range_validator_wrapper, lower=lower, upper=upper))


def int_phenotype() -> PlainSerializer:
    return PlainSerializer(lambda x: int(x), return_type=int)


def float_phenotype() -> PlainSerializer:
    return PlainSerializer(lambda x: x, return_type=float)


def bool_phenotype() -> PlainSerializer:
    return PlainSerializer(lambda x: x > 0, return_type=bool)


def random_default_range(lower: float, upper: float) -> Any:
    return Field(default_factory=lambda: random.uniform(lower, upper))  # noqa: S311


type ChromosomeType = type[Chromosome]


def random_chromosome(chromosome_type: ChromosomeType) -> Any:
    return Field(default_factory=lambda: chromosome_type())


class Genotype(Chromosome):
    pass


def new_organism_id() -> domain.UID:
    return domain.UID(str(bson.ObjectId()))


class Organism(domain.Entity):
    tickers: list[str] = Field(default_factory=list)
    genes: Genes = Field(default_factory=dict)
    model: bytes = b""
    lr: list[float] = Field(default_factory=list)
    llh: list[float] = Field(default_factory=list)
    training_time: int = 0
    ub: float = float("inf")

    @computed_field
    def wins(self) -> int:
        return len(self.lr)

    def make_child(self, parent1: Organism, parent2: Organism, scale: float) -> Genes:
        genotype = Genotype.model_validate(self.genes)
        genotype1 = Genotype.model_validate(parent1.genes)
        genotype2 = Genotype.model_validate(parent2.genes)

        child = genotype.make_child(genotype1, genotype2, scale)

        return child.genes

    @field_validator("tickers")
    def _tickers_must_be_sorted(cls, tickers: list[str]) -> list[str]:
        tickers_pairs = itertools.pairwise(tickers)

        if not all(ticker < next_ for ticker, next_ in tickers_pairs):
            raise ValueError("tickers not sorted")

        return tickers

    @model_validator(mode="after")
    def _stats_must_be_same_length(self) -> Self:
        if len(self.lr) != len(self.llh):
            raise ValueError("lr and llh must be same length")

        return self


class SubGene(Chromosome):
    fff: Annotated[
        float,
        gene_range(0, 10),
        int_phenotype(),
    ] = random_default_range(1, 9)


class Gene(Chromosome):
    value: Annotated[
        float,
        gene_range(0, 20),
        int_phenotype(),
    ] = random_default_range(1, 19)
    sub: SubGene = random_chromosome(SubGene)
