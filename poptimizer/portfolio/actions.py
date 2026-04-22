import asyncio
import statistics
from datetime import UTC, datetime, timedelta
from typing import Annotated, Final, Literal, Protocol

from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    PositiveInt,
)

from poptimizer.core import domain, fsm
from poptimizer.data.events import QuotesUpdated
from poptimizer.data.moex import quotes, securities
from poptimizer.evolve.evolution import evolve
from poptimizer.portfolio import events
from poptimizer.portfolio.port import portfolio

_NANOS_IN_RUB: Final = 10**9
_CHECKED_INTERVAL: Final = timedelta(minutes=30)


class RevaluePortfolioAction:
    async def __call__(self, ctx: fsm.Ctx, event: QuotesUpdated) -> None:
        port = await ctx.get_for_update(portfolio.Portfolio)

        if _update_holding_period(port, event.trading_days):
            await self._update(ctx, port, event.trading_days)

        ctx.send(events.PortfolioRevalued(trading_days=event.trading_days))

    async def _update(self, ctx: fsm.Ctx, port: portfolio.Portfolio, trading_days: list[domain.Day]) -> None:
        port.illiquid.clear()

        evolution = await ctx.get_for_update(evolve.Evolution)

        sec_cache = await _prepare_sec_cache(ctx, port.forecast_days, evolution.minimal_returns_days + 1, trading_days)
        min_turnover = _calc_min_turnover(port, sec_cache)

        old_value = port.value()
        _update_existing_positions(ctx, port, sec_cache, min_turnover)
        _add_new_liquid(ctx, port, sec_cache, min_turnover)

        if old_value:
            new_value = port.value()
            change = new_value / old_value - 1
            ctx.warning(f"Portfolio value changed {change:.2%} - {old_value:_.0f} -> {new_value:_.0f}")


def _update_holding_period(port: portfolio.Portfolio, trading_days: list[domain.Day]) -> bool:
    if port.day >= trading_days[-1]:
        return False

    new_days = 0

    for day in reversed(trading_days):
        if day <= port.day:
            break

        new_days += 1

    match port.open_positions():
        case 0:
            port.holding_period = 0
        case open_positions:
            port.holding_period *= 1 - min(open_positions, port.new_positions) / open_positions
            port.holding_period += new_days

    port.new_positions = 0
    port.day = trading_days[-1]

    return True


async def _prepare_sec_cache(
    ctx: fsm.Ctx,
    forecast_days: PositiveInt,
    minimal_candles: PositiveInt,
    trading_days: list[domain.Day],
) -> dict[domain.Ticker, portfolio.Position]:
    sec_table = await ctx.get(securities.Securities)

    async with asyncio.TaskGroup() as tg:
        quotes_tasks = [tg.create_task(ctx.get(quotes.Quotes, domain.UID(sec.ticker))) for sec in sec_table.df]

    cache: dict[domain.Ticker, portfolio.Position] = {}

    turnover_days = set(trading_days[-forecast_days:])

    for sec, quotes_task in zip(sec_table.df, quotes_tasks, strict=True):
        df = quotes_task.result().df

        if not df:
            continue

        turnover = 0
        if len(df) >= minimal_candles:
            turnover_data = [row.turnover for row in df[-forecast_days:] if row.day in turnover_days]
            if turnover_data:
                turnover = statistics.median(turnover_data)

        cache[sec.ticker] = portfolio.Position(
            ticker=sec.ticker,
            lot=sec.lot,
            price=df[-1].close,
            turnover=turnover,
        )

    return cache


def _calc_min_turnover(
    port: portfolio.Portfolio,
    sec_cache: dict[domain.Ticker, portfolio.Position],
) -> float:
    min_turnover = port.cash_value()

    for position in port.positions:
        if new_position := sec_cache.get(position.ticker):
            min_turnover = max(min_turnover, new_position.price * position.quantity())

    return min_turnover


def _update_existing_positions(
    ctx: fsm.Ctx,
    port: portfolio.Portfolio,
    sec_cache: dict[domain.Ticker, portfolio.Position],
    min_turnover: float,
) -> None:
    updated_positions: list[portfolio.Position] = []

    for position in port.positions:
        match sec_cache.pop(position.ticker, None):
            case None if not position.accounts:
                ctx.info("Not traded %s is removed from portfolio", position.ticker)
            case None:
                position.turnover = min_turnover
                updated_positions.append(position)
                port.illiquid.add(position.ticker)
                ctx.warning("Not traded %s is not removed from portfolio", position.ticker)
            case new_position if new_position.turnover < min_turnover and not position.accounts:
                ctx.info("Not liquid %s is removed from portfolio", position.ticker)
            case new_position if new_position.turnover < min_turnover:
                new_position.accounts = position.accounts
                new_position.turnover = min_turnover
                updated_positions.append(new_position)
                port.illiquid.add(position.ticker)
                ctx.warning("Not liquid %s is not removed from portfolio", position.ticker)
            case new_position if new_position.ticker in port.exclude and not position.accounts:
                ctx.info("%s from exclude list is removed from portfolio", new_position.ticker)
            case new_position if new_position.ticker in port.exclude:
                new_position.accounts = position.accounts
                updated_positions.append(new_position)
                port.illiquid.add(position.ticker)
                ctx.warning("%s from exclude list is not removed from portfolio", position.ticker)
            case new_position:
                new_position.accounts = position.accounts
                updated_positions.append(new_position)

    port.positions = updated_positions


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
        return max(
            0,
            int(
                sum(m.units for m in self.money)
                + sum(m.units for m in self.blocked)
                + (sum(m.nano for m in self.money) + sum(m.nano for m in self.blocked)) / _NANOS_IN_RUB
            ),
        )


class TinkoffClient(Protocol):
    def updatable_accounts(self) -> set[domain.AccName]: ...

    async def get_positions(self, account_name: domain.AccName) -> Positions: ...


def _add_new_liquid(
    ctx: fsm.Ctx,
    port: portfolio.Portfolio,
    sec_cache: dict[domain.Ticker, portfolio.Position],
    min_turnover: float,
) -> None:
    for ticker, position in sec_cache.items():
        if position.turnover > min_turnover and ticker not in port.exclude:
            n, _ = port.find_position(position.ticker)
            port.positions.insert(n, position)

            ctx.info("%s is added to portfolio", ticker)


class CheckPositionsAction:
    def __init__(self, tinkoff_client: TinkoffClient) -> None:
        self._tinkoff_client = tinkoff_client

    async def __call__(self, ctx: fsm.Ctx) -> None:
        port = await ctx.get_for_update(portfolio.Portfolio)

        now = _now()
        if now - port.checked_at < _CHECKED_INTERVAL:
            return

        port.checked_at = now

        accounts = await self._ensure_accounts(ctx, port)

        async with asyncio.TaskGroup() as tg:
            updated = [tg.create_task(self._update_account(ctx, port, acc_name)) for acc_name in accounts]

        if any([await task for task in updated]):
            port.updated_at = now

        ctx.send(events.PositionChecked(updated_at=port.updated_at))

    async def _ensure_accounts(
        self,
        ctx: fsm.Ctx,
        port: portfolio.Portfolio,
    ) -> set[domain.AccName]:
        updatable_accounts = self._tinkoff_client.updatable_accounts()

        new_accounts = updatable_accounts - port.account_names

        if new_accounts:
            port = await ctx.get_for_update(portfolio.Portfolio)

            for acc_name in new_accounts:
                port.create_acount(acc_name)

            ctx.warning("New accounts created: %s", ", ".join(sorted(new_accounts)))

        return updatable_accounts

    async def _update_account(
        self,
        ctx: fsm.Ctx,
        port: portfolio.Portfolio,
        acc_name: domain.AccName,
    ) -> bool:
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
            ctx.warning(
                "Account %s can't be updated with unknown %s: %d",
                acc_name,
                ticker,
                quantity,
            )

        if not for_update:
            return False

        for ticker, quantity_current, quantity_new in for_update:
            port.update_position(acc_name, ticker, quantity_new)

            ctx.warning(
                "%s: %s %d -> %d",
                acc_name,
                ticker,
                quantity_current,
                quantity_new,
            )

        return True


def _now() -> datetime:
    return datetime.now(UTC)
