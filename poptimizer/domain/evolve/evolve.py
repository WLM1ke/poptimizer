from __future__ import annotations

import statistics
from enum import StrEnum
from typing import Final, Self

from pydantic import BaseModel, Field, NonNegativeFloat, PositiveInt, field_validator, model_validator

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.dl import datasets
from poptimizer.domain.evolve import genetics, genotype

_INITIAL_MINIMAL_RETURNS_DAYS: Final = datasets.minimal_returns_days(
    history_days=consts.INITIAL_HISTORY_DAYS_END,
    forecast_days=consts.FORECAST_DAYS,
    test_days=consts.INITIAL_TEST_DAYS,
)


class Metrics(BaseModel):
    duration: float
    alfas: list[float]
    llh: list[float]
    mean: list[list[float]]
    cov: list[list[float]]
    risk_tolerance: float


class Model(domain.Entity):
    tickers: tuple[domain.Ticker, ...] = Field(default_factory=tuple)
    genes: genetics.Genes = Field(default_factory=lambda: genotype.Genotype.model_validate({}).genes)
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
        genes = genotype.Genotype.model_validate(self.genes)
        risk_tol = genes.risk.risk_tolerance
        history = genes.batch.days.history

        return f"{self.__class__.__name__}(risk_tol={risk_tol:.2%}, history={history:.2f})"

    @property
    def phenotype(self) -> genetics.Phenotype:
        return genotype.Genotype.model_validate(self.genes).phenotype

    def make_child_genes(self, parent1: Model, parent2: Model, scale: float) -> genetics.Genes:
        model = genotype.Genotype.model_validate(self.genes)
        model1 = genotype.Genotype.model_validate(parent1.genes)
        model2 = genotype.Genotype.model_validate(parent2.genes)

        return model.make_child(model1, model2, scale).genes

    def update(self, day: domain.Day, tickers: tuple[domain.Ticker, ...], metrics: Metrics) -> None:
        self.day = day
        self.tickers = tickers
        self.alfa = statistics.mean(metrics.alfas)
        self.mean = metrics.mean
        self.cov = metrics.cov
        self.risk_tolerance = metrics.risk_tolerance


class State(StrEnum):
    EVAL_NEW_BASE_MODEL = "evaluating new base model"
    EVAL_MODEL = "evaluating model"
    REEVAL_CURRENT_BASE_MODEL = "reevaluating current base model"
    CREATE_NEW_MODEL = "creating new model"


class Evolution(domain.Entity):
    state: State = State.EVAL_NEW_BASE_MODEL
    step: PositiveInt = 1
    tickers: tuple[domain.Ticker, ...] = Field(default_factory=tuple)
    base_model_uid: domain.UID = domain.UID("")
    alfas: list[float] = Field(default_factory=list)
    llh: list[float] = Field(default_factory=list)
    duration: NonNegativeFloat = 0
    t_critical: float = -7
    minimal_returns_days: int = _INITIAL_MINIMAL_RETURNS_DAYS

    def init_new_day(self, day: domain.Day, tickers: tuple[domain.Ticker, ...]) -> None:
        self.day = day
        self.tickers = tickers
        self.step = 1
        self.state = State.EVAL_NEW_BASE_MODEL

    def adj_t_critical(self, duration: NonNegativeFloat) -> float:
        return self.t_critical * min(1, self.duration / duration)
