import statistics
from functools import cached_property
from typing import Final, Self, cast

import bson
from pydantic import (
    BaseModel,
    Field,
    FiniteFloat,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    model_validator,
)
from scipy import stats  # type: ignore[reportMissingTypeStubs]

from poptimizer.core import consts, domain, fsm
from poptimizer.evolve.dl import datasets
from poptimizer.evolve.evolution import genetics, genotype
from poptimizer.portfolio.port import portfolio

_INITIAL_MINIMAL_RETURNS_DAYS: Final = datasets.Days(
    history=consts.INITIAL_HISTORY_DAYS_END,
    forecast=consts.INITIAL_FORECAST_DAYS,
    test=consts.INITIAL_TEST_DAYS,
).minimal_returns_days
_PARENT_COUNT: Final = 2
_OPTIMAL_ACCEPTANCE_RATE: Final = 0.234


def random_model_uid() -> domain.UID:
    return domain.UID(str(bson.ObjectId()))


class TestResults(BaseModel):
    alfa: list[float]
    llh: list[float]
    ret: float

    def __str__(self) -> str:
        alfa = statistics.mean(self.alfa)
        llh = statistics.mean(self.llh)

        return f"{self.__class__.__name__}(alfa={alfa:.2%}, ret={self.ret:.2%}, llh={llh:.2f})"


class Model(domain.Entity):
    day: domain.Day = consts.START_DAY
    genes: genetics.Genes = Field(default_factory=lambda: genotype.Genotype.model_validate({}).genes)
    train_load: NonNegativeInt = 0
    test_days: NonNegativeInt = 0
    mean: list[list[FiniteFloat]] = Field(default_factory=list[list[FiniteFloat]])
    cov: list[list[FiniteFloat]] = Field(default_factory=list[list[FiniteFloat]])

    @model_validator(mode="after")
    def _match_length(self) -> Self:
        n = len(self.mean)

        if any(len(row) != 1 for row in self.mean):
            raise ValueError("invalid mean")

        if len(self.cov) != n:
            raise ValueError("invalid cov")

        if any(len(row) != n for row in self.cov):
            raise ValueError("invalid cov")

        return self

    def __str__(self) -> str:
        risk_tol = self.genotype.risk.risk_tolerance
        history = self.genotype.batch.history_days

        return f"{self.__class__.__name__}(risk_aversion={1 - risk_tol:.2%}, history={history:.2f})"

    @cached_property
    def genotype(self) -> genotype.Genotype:
        return genotype.Genotype.model_validate(self.genes)

    @property
    def phenotype(self) -> genetics.Phenotype:
        return self.genotype.phenotype

    def child_genes(self, parent1: Model, parent2: Model, scale: float) -> genetics.Genes:
        model = self.genotype
        model1 = parent1.genotype
        model2 = parent2.genotype

        return model.make_child(model1, model2, scale).genes


class Evolution(domain.Entity):
    day: domain.Day = consts.START_DAY
    tickers: domain.Tickers = Field(default_factory=tuple)
    forecast_days: PositiveInt = 1
    test_days: PositiveInt = 1
    minimal_returns_days: int = _INITIAL_MINIMAL_RETURNS_DAYS
    step: PositiveInt = 1
    alfa: list[FiniteFloat] = Field(default_factory=list[FiniteFloat])
    llh: list[FiniteFloat] = Field(default_factory=list[FiniteFloat])
    next_model: domain.UID = Field(default_factory=random_model_uid, min_length=1)
    radius: PositiveFloat = Field(default=1, ge=1)

    @model_validator(mode="after")
    def _match_length(self) -> Self:
        if len(self.llh) != len(self.alfa):
            raise ValueError("alfas and llh mismatch")

        return self

    def init_day(
        self,
        port: portfolio.Portfolio,
    ) -> None:
        self.day = port.day
        self.tickers = port.tickers
        self.forecast_days = port.forecast_days
        self.alfa = []
        self.llh = []
        self.step = 1

    def new_base(self, results: TestResults) -> None:
        self.alfa = results.alfa
        self.llh = results.llh

    def model_rejected(self) -> None:
        self.radius += 1 / self.test_days

    def model_accepted(self) -> None:
        self.radius -= (1 - _OPTIMAL_ACCEPTANCE_RATE) / _OPTIMAL_ACCEPTANCE_RATE / self.test_days

        if self.radius < 1:
            self.radius = 1
            self.test_days += 1


async def make_new_model(ctx: fsm.Ctx, evolution: Evolution, model: Model) -> domain.UID:
    parents = await ctx.sample_models(_PARENT_COUNT)
    if len({parent.uid for parent in parents}) != _PARENT_COUNT:
        parents = [Model(uid=model.uid) for _ in range(_PARENT_COUNT)]

    new_model = await ctx.get_for_update(Model, random_model_uid())
    new_model.genes = model.child_genes(parents[0], parents[1], 1 / evolution.radius)
    new_model.train_load = model.train_load

    return new_model.uid


async def is_accepted(
    ctx: fsm.Ctx,
    evolution: Evolution,
    model: Model,
    results: TestResults,
) -> bool:
    alfa_p = _probability(results.alfa, evolution.alfa)
    llh_p = _probability(results.llh, evolution.llh)
    ctx.info(f"Alfa probability - {alfa_p:.2%} / LLH probability - {llh_p:.2%}")

    if llh_p < consts.P_VALUE / 2:
        ctx.info(f"{model} rejected with {results} - low llh probability")
        await ctx.delete(model)

        return False

    count = await ctx.count_models()

    if alfa_p < consts.P_VALUE / 2:
        ctx.info(f"{model} rejected with {results} - low alfa probability")
        if count > evolution.test_days:
            await ctx.delete(model)

        return False

    ctx.info(f"{model} accepted with {results}")

    return True


def _probability(target: list[float], base: list[float]) -> float:
    alfa, beta = 1, 1
    for t, b in zip(target, base, strict=False):
        sign = t > b
        alfa += sign
        beta += 1 - sign

    return cast("float", stats.beta(alfa, beta).sf(0.5))  # type: ignore[reportUnknownMemberType]
