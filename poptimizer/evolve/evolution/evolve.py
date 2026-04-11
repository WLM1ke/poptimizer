import statistics
from functools import cached_property
from typing import Final, Self, cast

import bson
from pydantic import (
    BaseModel,
    Field,
    FiniteFloat,
    NonPositiveFloat,
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
MINIMAL_TEST_DAYS: Final = 2


def random_model_uid() -> domain.UID:
    return domain.UID(str(bson.ObjectId()))


class TestResults(BaseModel):
    llh: list[FiniteFloat]
    alfa: FiniteFloat
    ret: FiniteFloat

    def is_low_return(self) -> bool:
        return min(self.alfa, self.ret) < 0

    def __str__(self) -> str:
        llh = statistics.mean(self.llh)

        return f"{self.__class__.__name__}(alfa={self.alfa:.2%}, ret={self.ret:.2%}, llh={llh:.2f})"


class Model(domain.Entity):
    day: domain.Day = consts.START_DAY
    genes: genetics.Genes = Field(default_factory=lambda: genotype.Genotype.model_validate({}).genes)
    negative_alfa: NonPositiveFloat = 0
    llh: FiniteFloat = 0
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

        return f"{self.__class__.__name__}(risk_aversion={1 - risk_tol:.2%}, history={history:.2f}, llh={self.llh:.2f})"

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
    test_days: float = Field(2, ge=MINIMAL_TEST_DAYS)
    minimal_returns_days: int = _INITIAL_MINIMAL_RETURNS_DAYS
    step: PositiveInt = 1
    alfa: FiniteFloat = 0
    llh: list[FiniteFloat] = Field(default_factory=list[FiniteFloat])
    next_model: domain.UID = Field(default_factory=random_model_uid, min_length=1)
    radius: PositiveFloat = Field(default=1, ge=1)

    def init_day(
        self,
        port: portfolio.Portfolio,
    ) -> None:
        self.day = port.day
        self.tickers = port.tickers
        self.forecast_days = port.forecast_days
        self.alfa = 0
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
            self.test_days += 1 - self.radius
            self.radius = 1


async def make_new_model(ctx: fsm.Ctx, evolution: Evolution, model: Model) -> domain.UID:
    parents = await ctx.sample_models(_PARENT_COUNT)
    if len({parent.uid for parent in parents}) != _PARENT_COUNT:
        parents = [Model(uid=model.uid) for _ in range(_PARENT_COUNT)]

    new_model = await ctx.get_for_update(Model, random_model_uid())
    new_model.genes = model.child_genes(parents[0], parents[1], 1 / evolution.radius)

    return new_model.uid


async def is_accepted(
    ctx: fsm.Ctx,
    evolution: Evolution,
    model: Model,
    results: TestResults,
) -> bool:
    if results.is_low_return() and results.alfa < evolution.alfa:
        ctx.info(f"{model} rejected with {results} - low alfa")
        evolution.test_days += 1

        return False

    evolution.test_days = max(MINIMAL_TEST_DAYS, evolution.test_days - consts.P_VALUE / (1 - consts.P_VALUE))

    llh_p = _probability(results.llh, evolution.llh)

    if llh_p < consts.P_VALUE:
        ctx.info(f"{model} rejected with {results} - low llh probability {llh_p:.2%}")

        return False

    ctx.info(f"{model} accepted with {results} - high llh probability {llh_p:.2%}")

    return True


def _probability(target: list[float], base: list[float]) -> float:

    return cast(
        "float",
        stats.ttest_1samp(  # type: ignore[reportUnknownMemberType]
            [t - b for t, b in zip(target, base, strict=False)],
            0,
            alternative="less",
        ).pvalue,  # pyright: ignore[reportAttributeAccessIssue]
    )
