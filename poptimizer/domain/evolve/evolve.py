from __future__ import annotations

import statistics
from enum import StrEnum
from typing import Final, Self

from pydantic import (
    Field,
    FiniteFloat,
    NonNegativeFloat,
    NonPositiveFloat,
    PositiveInt,
    computed_field,
    model_validator,
)

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.dl import datasets
from poptimizer.domain.evolve import genetics, genotype

_INITIAL_MINIMAL_RETURNS_DAYS: Final = datasets.Days(
    history=consts.INITIAL_HISTORY_DAYS_END,
    forecast=consts.INITIAL_FORECAST_DAYS,
    test=consts.INITIAL_TEST_DAYS,
).minimal_returns_days


class Model(domain.Entity):
    tickers: domain.Tickers = Field(default_factory=tuple)
    forecast_days: PositiveInt = 1
    genes: genetics.Genes = Field(default_factory=lambda: genotype.Genotype.model_validate({}).genes)
    duration: float = 0
    alfa: list[FiniteFloat] = Field(default_factory=list)
    llh: list[FiniteFloat] = Field(default_factory=list)
    mean: list[list[FiniteFloat]] = Field(default_factory=list)
    cov: list[list[FiniteFloat]] = Field(default_factory=list)
    risk_tolerance: FiniteFloat = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def _match_length(self) -> Self:
        if len(self.llh) != len(self.alfa):
            raise ValueError("alfa and llh mismatch")

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
        history = genes.batch.history_days

        return f"{self.__class__.__name__}(ver={self.ver}, risk_aversion={1 - risk_tol:.2%}, history={history:.2f})"

    @computed_field
    @property
    def alfa_mean(self) -> float:
        return statistics.mean(self.alfa or [0])

    @computed_field
    @property
    def llh_mean(self) -> float:
        return statistics.mean(self.llh or [0])

    @property
    def stats(self) -> str:
        return f"Model(alfa={self.alfa_mean:.2%}, llh={self.llh_mean:.4f})"

    @property
    def phenotype(self) -> genetics.Phenotype:
        return genotype.Genotype.model_validate(self.genes).phenotype

    def make_child_genes(self, parent1: Model, parent2: Model, scale: float) -> genetics.Genes:
        model = genotype.Genotype.model_validate(self.genes)
        model1 = genotype.Genotype.model_validate(parent1.genes)
        model2 = genotype.Genotype.model_validate(parent2.genes)

        return model.make_child(model1, model2, scale).genes


class State(StrEnum):
    EVAL_NEW_BASE_MODEL = "evaluating new base model"
    EVAL_MODEL = "evaluating model"
    REEVAL_CURRENT_BASE_MODEL = "reevaluating current base model"
    CREATE_NEW_MODEL = "creating new model"


class Evolution(domain.Entity):
    tickers: domain.Tickers = Field(default_factory=tuple)
    forecast_days: PositiveInt = 1
    state: State = State.EVAL_NEW_BASE_MODEL
    step: PositiveInt = 1
    base_model_uid: domain.UID = domain.UID("")
    alfa: list[FiniteFloat] = Field(default_factory=list)
    llh: list[FiniteFloat] = Field(default_factory=list)
    duration: NonNegativeFloat = 0
    test_days: float = Field(default=2, ge=1)
    alfa_delta_critical: NonPositiveFloat = 0
    llh_delta_critical: NonPositiveFloat = 0
    minimal_returns_days: int = _INITIAL_MINIMAL_RETURNS_DAYS

    @model_validator(mode="after")
    def _match_length(self) -> Self:
        if len(self.llh) != len(self.alfa):
            raise ValueError("alfas and llh mismatch")

        return self

    def init_new_day(
        self,
        day: domain.Day,
        tickers: domain.Tickers,
        forecast_days: int,
    ) -> None:
        self.day = day
        self.tickers = tickers
        self.forecast_days = forecast_days
        self.step = 1
        self.minimal_returns_days = max(1, self.minimal_returns_days - 1)
        self.state = State.EVAL_NEW_BASE_MODEL

    def adj_alfa_delta_critical(self, duration: NonNegativeFloat) -> float:
        return self.alfa_delta_critical * min(1, self.duration / duration)

    def adj_llh_delta_critical(self, duration: NonNegativeFloat) -> float:
        return self.llh_delta_critical * min(1, self.duration / duration)

    def new_base(self, model: Model) -> None:
        self.base_model_uid = model.uid
        self.alfa = model.alfa
        self.llh = model.llh
        self.duration = model.duration
