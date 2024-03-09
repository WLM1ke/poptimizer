import asyncio
import itertools
from enum import IntEnum, auto
from typing import Annotated

from pydantic import Field, PositiveInt
from pydantic.functional_validators import AfterValidator

from poptimizer.core import domain
from poptimizer.data import contracts as data
from poptimizer.portfolio import contracts as portfolio


def _sorted_tickers(tickers: list[domain.Ticker]) -> list[domain.Ticker]:
    ticker_pairs = itertools.pairwise(ticker for ticker in tickers)

    if not all(ticker < next_ for ticker, next_ in ticker_pairs):
        raise ValueError("tickers not sorted")

    return tickers


class Evolution(domain.Entity):
    tickers: Annotated[list[domain.Ticker], AfterValidator(_sorted_tickers)] = Field(default_factory=list)
    target_population: PositiveInt = 1


class EvolutionStepEnded(domain.Event):
    day: domain.Day


class EvolutionState(IntEnum):
    INIT = auto()
    RUNNING = auto()
    FINISHED = auto()


class EvolutionEventHandler:
    def __init__(self) -> None:
        self._state = EvolutionState.INIT

    async def handle(
        self,
        ctx: domain.Ctx,
        event: data.DayStarted | portfolio.PortfolioDataUpdated | EvolutionStepEnded | domain.StopEvent,
    ) -> None:
        match event:
            case data.DayStarted():
                evolution = await ctx.get(Evolution, for_update=False)

                if self._state is EvolutionState.INIT and evolution.ver > 0:
                    self._state = EvolutionState.RUNNING
                    ctx.publish(EvolutionStepEnded(day=evolution.day))
            case portfolio.PortfolioDataUpdated():
                evolution = await ctx.get(Evolution)

                evolution.day = event.day
                evolution.tickers = sorted(event.positions_weight)

                if self._state is EvolutionState.INIT:
                    self._state = EvolutionState.RUNNING
                    ctx.publish(EvolutionStepEnded(day=evolution.day))
            case EvolutionStepEnded():
                await self._step(ctx, event.day)
            case domain.StopEvent():
                self._state = EvolutionState.FINISHED

    async def _step(self, ctx: domain.Ctx, day: domain.Day) -> None:
        await asyncio.sleep(3600)

        if self._state is not EvolutionState.FINISHED:
            ctx.publish(EvolutionStepEnded(day=day))
