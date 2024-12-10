from __future__ import annotations

import statistics
from enum import StrEnum
from typing import Final, Self

from pydantic import Field, NonNegativeFloat, PositiveInt, computed_field, field_validator, model_validator

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.dl import datasets
from poptimizer.domain.evolve import genetics, genotype

_INITIAL_MINIMAL_RETURNS_DAYS: Final = datasets.minimal_returns_days(
    history_days=consts.INITIAL_HISTORY_DAYS_END,
    forecast_days=consts.FORECAST_DAYS,
    test_days=consts.INITIAL_TEST_DAYS,
)


class Model(domain.Entity):
    tickers: tuple[domain.Ticker, ...] = Field(default_factory=tuple)
    genes: genetics.Genes = Field(default_factory=lambda: genotype.Genotype.model_validate({}).genes)
    duration: float = 0
    alfas: list[float] = Field(default_factory=list)
    llh: list[float] = Field(default_factory=list)
    mean: list[list[float]] = Field(default_factory=list)
    cov: list[list[float]] = Field(default_factory=list)
    risk_tolerance: float = Field(default=0, ge=0, le=1)

    _must_be_sorted_by_ticker = field_validator("tickers")(domain.sorted_tickers)

    @model_validator(mode="after")
    def _match_length(self) -> Self:
        if len(self.alfas) != len(self.llh):
            raise ValueError("invalid metrics length")

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
    state: State = State.EVAL_NEW_BASE_MODEL
    step: PositiveInt = 1
    tickers: tuple[domain.Ticker, ...] = Field(default_factory=tuple)
    base_model_uid: domain.UID = domain.UID("")
    alfas: list[float] = Field(default_factory=list)
    llh: list[float] = Field(default_factory=list)
    duration: NonNegativeFloat = 0
    test_days: int = Field(default=2, ge=2)
    more_tests: bool = True
    t_critical: float = -7
    minimal_returns_days: int = _INITIAL_MINIMAL_RETURNS_DAYS

    def init_new_day(self, day: domain.Day, tickers: tuple[domain.Ticker, ...]) -> None:
        self.day = day
        self.tickers = tickers
        self.step = 1
        self.more_tests = True
        self.state = State.EVAL_NEW_BASE_MODEL

    def adj_t_critical(self, duration: NonNegativeFloat) -> float:
        return self.t_critical * min(1, self.duration / duration)

    def new_base(self, model: Model) -> None:
        self.base_model_uid = model.uid
        self.alfas = model.alfas
        self.llh = model.llh
        self.duration = model.duration
