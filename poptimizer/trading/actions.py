from typing import Protocol

from poptimizer.core import domain, fsm
from poptimizer.portfolio.models import portfolio
from poptimizer.trading.models import trading


class TinkoffClient(Protocol):
    def updatable_accounts(self) -> set[domain.AccName]: ...
    async def get_orders(self, account_name: domain.AccName) -> list[domain.Ticker]: ...


class InitTradingStateAction:
    async def __call__(self, ctx: fsm.Ctx) -> None:
        trading_state = await ctx.get_for_update(trading.TradingState)
        port = await ctx.get(portfolio.Portfolio)

        if trading_state.day != port.day:
            trading_state.init_day(port)


class CancelStaleOrdersAction:
    def __init__(self, tinkoff_client: TinkoffClient) -> None:
        self._tinkoff_client = tinkoff_client

    async def __call__(self, ctx: fsm.Ctx) -> None:
        for account_name in self._tinkoff_client.updatable_accounts():
            tickers = await self._tinkoff_client.get_orders(account_name)
            if tickers:
                ctx.warning("%s active orders - %s", account_name, ", ".join(tickers))
