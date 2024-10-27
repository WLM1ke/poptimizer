from __future__ import annotations

import functools
import random
from typing import Any, Self

from pydantic import AfterValidator, BaseModel, Field, PlainSerializer

from poptimizer import errors

type Genes = dict[str, float | Genes]
type Phenotype = dict[str, Any]


class Chromosome(BaseModel):
    @property
    def phenotype(self) -> Phenotype:
        return self.model_dump()

    @property
    def genes(self) -> Genes:
        genes: Genes = {}

        for gene, value in self:
            match value:
                case float():
                    genes[gene] = value
                case Chromosome():
                    genes[gene] = value.genes
                case _:
                    raise errors.DomainError(f"unknown gene type {type(value)}")

        return genes

    def make_child(self, parent1: Self, parent2: Self, scale: float) -> Self:
        genes1 = dict(parent1)
        genes2 = dict(parent2)

        child = {}

        for gene, value in self:
            match value:
                case float():
                    child[gene] = value + (genes1[gene] - genes2[gene]) * scale * random.gauss()
                case Chromosome():
                    child[gene] = value.make_child(genes1[gene], genes2[gene], scale)
                case _:
                    raise errors.DomainError(f"unknown gene {gene} type {type(value)}")

        return self.model_validate(child)


def _range_validator_wrapper(value: float, lower: float | None, upper: float | None) -> float:
    if lower is not None and value < lower:
        return _range_validator_wrapper(lower + (lower - value), lower, upper)

    if upper is not None and value > upper:
        return _range_validator_wrapper(upper - (value - upper), lower, upper)

    return value


def gene_range(*, lower: float | None = None, upper: float | None = None) -> AfterValidator:
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
    return Field(default_factory=chromosome_type)
