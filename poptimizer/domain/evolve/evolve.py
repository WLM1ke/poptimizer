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
from poptimizer.domain.dl import features
from poptimizer.domain.evolve import genetics, genotype

_INITIAL_MINIMAL_RETURNS_DAYS: Final = features.Days(
    history=consts.INITIAL_HISTORY_DAYS_END,
    forecast=consts.INITIAL_FORECAST_DAYS,
    test=consts.INITIAL_POPULATION,
).minimal_returns_days


class Model(domain.Entity):
    tickers: domain.Tickers = Field(default_factory=tuple)
    forecast_days: PositiveInt = 1
    genes: genetics.Genes = Field(default_factory=lambda: genotype.Genotype.model_validate({}).genes)
    duration: float = 0
    alfas: list[FiniteFloat] = Field(default_factory=list)
    mean: list[list[FiniteFloat]] = Field(default_factory=list)
    cov: list[list[FiniteFloat]] = Field(default_factory=list)
    risk_tolerance: FiniteFloat = Field(default=0, ge=0, le=1)

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
        history = genes.batch.history_days

        return f"{self.__class__.__name__}(ver={self.ver}, risk_tol={risk_tol:.2%}, history={history:.2f})"

    @computed_field
    def alfa(self) -> float:
        if not self.alfas:
            return 0

        return statistics.mean(self.alfas)

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
    portfolio_ver: domain.Version = domain.Version(0)
    tickers: domain.Tickers = Field(default_factory=tuple)
    forecast_days: PositiveInt = 1
    state: State = State.EVAL_NEW_BASE_MODEL
    step: PositiveInt = 1
    base_model_uid: domain.UID = domain.UID("")
    alfas: list[float] = Field(default_factory=list)
    duration: NonNegativeFloat = 0
    test_days: int = Field(default=2, ge=2)
    delta_critical: NonPositiveFloat = 0
    minimal_returns_days: int = _INITIAL_MINIMAL_RETURNS_DAYS

    def init_new_day(self, day: domain.Day) -> None:
        self.day = day
        self.step = 1
        self.state = State.EVAL_NEW_BASE_MODEL

    def update_portfolio_ver(
        self,
        portfolio_ver: domain.Version,
        tickers: domain.Tickers,
        forecast_days: int,
    ) -> None:
        self.portfolio_ver = portfolio_ver
        self.tickers = tickers
        self.forecast_days = forecast_days

    def adj_delta_critical(self, duration: NonNegativeFloat) -> float:
        return self.delta_critical * min(1, self.duration / duration)

    def new_base(self, model: Model) -> None:
        self.base_model_uid = model.uid
        self.alfas = model.alfas
        self.duration = model.duration
