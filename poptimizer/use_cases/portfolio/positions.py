import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Final, Literal, Protocol

from pydantic import BaseModel, Field
from pydantic.functional_validators import BeforeValidator

from poptimizer.domain import domain
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler

_UPDATE_INTERVAL: Final = timedelta(minutes=30)
_NANOS_IN_RUB: Final = 10**9


def _str_to_int(v: str | int) -> int:
    if isinstance(v, str):
        return int(v)

    return v


type Int = Annotated[int, BeforeValidator(_str_to_int)]


class Money(BaseModel):
    currency: Literal["rub"]
    units: Int
    nano: int


class Position(BaseModel):
    ticker: domain.Ticker
    # Бумаг после блокировки под заявки на продажу
    balance: Int
    # Бумаг заблокировано под заявки на продажу
    blocked: Int

    @property
    def total(self) -> int:
        return self.balance + self.blocked


class Positions(BaseModel):
    # Денег после блокировки под заявки на покупку
    money: list[Money] = Field(min_length=1, max_length=1)
    # Денег заблокировано под заявки на покупку
    blocked: list[Money] = Field(min_length=0, max_length=1)
    securities: list[Position]

    def cash(self) -> int:
        return int(
            sum(m.units for m in self.money)
            + sum(m.units for m in self.blocked)
            + (sum(m.nano for m in self.money) + sum(m.nano for m in self.blocked)) / _NANOS_IN_RUB
        )


class TinkoffClient(Protocol):
    def updatable_accounts(self) -> set[domain.AccName]: ...

    async def get_positions(self, account_name: domain.AccName) -> Positions: ...


class PositionsHandler:
    def __init__(self, tinkoff_client: TinkoffClient) -> None:
        self._lgr = logging.getLogger()
        self._tinkoff_client = tinkoff_client
        self._last_check = datetime.now(UTC) - _UPDATE_INTERVAL

    async def __call__(self, ctx: handler.Ctx, msg: handler.DataChecked) -> None:  # noqa: ARG002
        if not self._need_update():
            return

        port = await ctx.get(portfolio.Portfolio)

        updatable_accounts = self._tinkoff_client.updatable_accounts()

        await self._add_accounts(ctx, updatable_accounts - port.account_names)

        async with asyncio.TaskGroup() as tg:
            for acc_name in updatable_accounts:
                tg.create_task(self._update_account(ctx, port, acc_name))

        self._last_check = datetime.now(UTC)

    def _need_update(self) -> bool:
        return datetime.now(UTC) - self._last_check > _UPDATE_INTERVAL

    async def _add_accounts(
        self,
        ctx: handler.Ctx,
        new_accounts: set[domain.AccName],
    ) -> None:
        if not new_accounts:
            return

        port = await ctx.get_for_update(portfolio.Portfolio)

        for acc_name in new_accounts:
            port.create_acount(acc_name)

        self._lgr.warning("New accounts created: %s", ", ".join(sorted(new_accounts)))

    async def _update_account(
        self,
        ctx: handler.Ctx,
        port: portfolio.Portfolio,
        acc_name: domain.AccName,
    ) -> None:
        positions = await self._tinkoff_client.get_positions(acc_name)
        for_update: list[tuple[domain.Ticker, int, int]] = []

        cash_current = port.cash_value(acc_name)
        cash_new = positions.cash()
        if cash_current != cash_new:
            for_update.append((domain.CashTicker, cash_current, cash_new))

        position_cache = {pos.ticker: pos.total for pos in positions.securities}

        for pos in port.positions:
            quantity_current = pos.accounts.get(acc_name, 0)
            quantity_new = position_cache.pop(pos.ticker, 0)
            if quantity_current != quantity_new:
                for_update.append((pos.ticker, quantity_current, quantity_new))

        for ticker, quantity in sorted(position_cache.items()):
            self._lgr.warning(
                "Account %s can't be updated with unknown %s: %d",
                acc_name,
                ticker,
                quantity,
            )

        if not for_update:
            return

        port = await ctx.get_for_update(portfolio.Portfolio)

        for ticker, quantity_current, quantity_new in for_update:
            port.update_position(acc_name, ticker, quantity_new)

            self._lgr.warning(
                "%s: %s %d -> %d",
                acc_name,
                ticker,
                quantity_current,
                quantity_new,
            )
