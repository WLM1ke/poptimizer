from __future__ import annotations

import itertools
from typing import Self

from pydantic import Field, field_validator, model_validator

from poptimizer.domain import domain
from poptimizer.domain.evolve import genetics, genotype


class Organism(domain.Entity):
    tickers: tuple[domain.Ticker, ...] = Field(default_factory=list)
    genes: genetics.Genes = Field(default_factory=dict)
    model: bytes = b""
    lr: list[float] = Field(default_factory=list)
    llh: list[float] = Field(default_factory=list)
    training_time: int = 0
    ub: float = 0

    @property
    def phenotype(self) -> genetics.Phenotype:
        return genotype.DLModel.model_validate(self.genes).phenotype

    def make_child(self, parent1: Organism, parent2: Organism, scale: float) -> genetics.Genes:
        model = genotype.DLModel.model_validate(self.genes)
        model1 = genotype.DLModel.model_validate(parent1.genes)
        model2 = genotype.DLModel.model_validate(parent2.genes)

        return model.make_child(model1, model2, scale).genes

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
