import asyncio
import statistics

from pydantic import (
    PositiveInt,
)

from poptimizer.core import domain, fsm
from poptimizer.data.events import QuotesUpdated
from poptimizer.data.evolve import evolve
from poptimizer.data.moex import quotes, securities
from poptimizer.portfolio import events
from poptimizer.portfolio.port import portfolio


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
            min_turnover = max(min_turnover, new_position.value())

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
