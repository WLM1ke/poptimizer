import functools
import random
from collections.abc import Iterable
from typing import Self, cast

from pydantic import AfterValidator, BaseModel, Field, PlainSerializer

from poptimizer.core import errors

type Genes = dict[str, float | Genes]
type PhenotypeValue = float | int | bool | str | dict[str, PhenotypeValue]
type Phenotype = dict[str, PhenotypeValue]


class Chromosome(BaseModel):
    @property
    def phenotype(self) -> Phenotype:
        return self.model_dump()

    @property
    def genes(self) -> Genes:
        genes: Genes = {}

        for gene, value in cast("Iterable[tuple[str, object]]", self):
            match value:
                case float():
                    genes[gene] = value
                case Chromosome():
                    genes[gene] = value.genes
                case _:
                    raise errors.DomainError(f"unknown gene type {type(value)}")

        return genes

    def make_child(self, parent1: Self, parent2: Self, scale: float) -> Self:
        genes1 = cast("dict[str, float | Chromosome]", dict(parent1))
        genes2 = cast("dict[str, float | Chromosome]", dict(parent2))

        child: dict[str, float | Chromosome] = {}

        for gene, value in cast("Iterable[tuple[str, object]]", self):
            match value:
                case float():
                    child[gene] = (
                        value + (cast("float", genes1[gene]) - cast("float", genes2[gene])) * scale * random.gauss()
                    )
                case Chromosome():
                    child[gene] = value.make_child(
                        cast("Self", genes1[gene]),
                        cast("Self", genes2[gene]),
                        scale,
                    )
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
    return PlainSerializer(int, return_type=int)


def _identity(value: float) -> float:
    return value


def _is_positive(value: float) -> bool:
    return value > 0


def _anneal_strategy(value: float) -> str:
    return "linear" if value > 0 else "cos"


def float_phenotype() -> PlainSerializer:
    return PlainSerializer(_identity, return_type=float)


def bool_phenotype() -> PlainSerializer:
    return PlainSerializer(_is_positive, return_type=bool)


def anneal_strategy_phenotype() -> PlainSerializer:
    return PlainSerializer(_anneal_strategy, return_type=str)


def phenotype_mapping(phenotype: Phenotype, key: str) -> Phenotype:
    value = phenotype[key]
    if not isinstance(value, dict):
        raise errors.DomainError(f"phenotype value {key} is not a mapping")

    return value


def phenotype_float(phenotype: Phenotype, key: str) -> float:
    value = phenotype[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise errors.DomainError(f"phenotype value {key} is not a number")

    return float(value)


def phenotype_int(phenotype: Phenotype, key: str) -> int:
    value = phenotype[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise errors.DomainError(f"phenotype value {key} is not an integer")

    return value


def phenotype_bool(phenotype: Phenotype, key: str) -> bool:
    value = phenotype[key]
    if not isinstance(value, bool):
        raise errors.DomainError(f"phenotype value {key} is not a boolean")

    return value


def phenotype_flags(phenotype: Phenotype, key: str) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for name, value in phenotype_mapping(phenotype, key).items():
        if not isinstance(value, bool):
            raise errors.DomainError(f"phenotype value {key}.{name} is not a boolean")
        flags[name] = value

    return flags


def random_default_range(lower: float, upper: float) -> float:
    return Field(default_factory=lambda: random.uniform(lower, upper))  # noqa: S311


def random_chromosome[T: Chromosome](chromosome_type: type[T]) -> T:
    return Field(default_factory=chromosome_type)
