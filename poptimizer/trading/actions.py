import random
from typing import Protocol

from poptimizer.core import domain, fsm
from poptimizer.trading import events


class TinkoffClient(Protocol):
    def updatable_accounts(self) -> set[domain.AccName]: ...
    async def get_orders(self, account_name: domain.AccName) -> list[domain.Ticker]: ...


class CheckMarketStateAction:
    async def __call__(self, ctx: fsm.Ctx) -> None:
        event = random.choice(  # noqa: S311
            [
                events.TradingDayChanged(),
                events.MarketClosed(),
                events.MarketOpened(),
            ]
        )
        ctx.send(event)


class InitTradingDayAction:
    async def __call__(self, ctx: fsm.Ctx) -> None: ...


class CancelObsoleteOrdersAction:
    async def __call__(self, ctx: fsm.Ctx) -> None:
        ctx.send(events.ObsoleteOrdersCanceled())


class SubmitBuyOrdersAction:
    async def __call__(self, ctx: fsm.Ctx) -> None:
        event = random.choice(  # noqa: S311
            [
                events.FreeCashLeft(),
                events.BuyOrdersSubmitted(),
            ]
        )
        ctx.send(event)


class SubmitSellOrdersAction:
    async def __call__(self, ctx: fsm.Ctx) -> None:
        ctx.send(events.SellOrdersSubmitted())
