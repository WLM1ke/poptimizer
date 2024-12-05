from __future__ import annotations

import statistics
from typing import TYPE_CHECKING, Self

from pydantic import Field, field_validator, model_validator

from poptimizer.domain import domain
from poptimizer.domain.evolve import genetics, genotype

if TYPE_CHECKING:
    from poptimizer.domain.dl import training


class Organism(domain.Entity):
    tickers: tuple[domain.Ticker, ...] = Field(default_factory=tuple)
    genes: genetics.Genes = Field(default_factory=lambda: genotype.DLModel.model_validate({}).genes)
    alfa: float = 0
    mean: list[list[float]] = Field(default_factory=list)
    cov: list[list[float]] = Field(default_factory=list)
    risk_tolerance: float = Field(default=0, ge=0, le=1)

    _must_be_sorted_by_ticker = field_validator("tickers")(domain.sorted_tickers)

    @model_validator(mode="after")
    def _match_length(self) -> Self:
        n = len(self.tickers)

        if len(self.mean) != n:
            raise ValueError("invalid mean")

        if any(len(row) != 1 for row in self.mean):
            raise ValueError("invalid mean")

        if len(self.cov) != n:
            raise ValueError("invalid cov")

        if any(len(row) != n for row in self.cov):
            raise ValueError("invalid cov")

        return self

    def __str__(self) -> str:
        genes = genotype.DLModel.model_validate(self.genes)
        risk_tol = genes.risk.risk_tolerance
        history = genes.batch.days.history

        return f"Organism(risk_tol={risk_tol:.2%}, history={history:.2f}) - alfa({self.alfa:.2%})"

    @property
    def phenotype(self) -> genetics.Phenotype:
        return genotype.DLModel.model_validate(self.genes).phenotype

    def make_child_genes(self, parent1: Organism, parent2: Organism, scale: float) -> genetics.Genes:
        model = genotype.DLModel.model_validate(self.genes)
        model1 = genotype.DLModel.model_validate(parent1.genes)
        model2 = genotype.DLModel.model_validate(parent2.genes)

        return model.make_child(model1, model2, scale).genes

    def update_stats(
        self,
        day: domain.Day,
        tickers: tuple[domain.Ticker, ...],
        result: training.Result,
    ) -> None:
        self.day = day
        self.tickers = tickers
        self.alfa = statistics.mean(result.alfas)
        self.mean = result.mean
        self.cov = result.cov
        self.risk_tolerance = result.risk_tolerance
