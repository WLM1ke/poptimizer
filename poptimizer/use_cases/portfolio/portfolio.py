import asyncio
import logging
import statistics

from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve
from poptimizer.domain.moex import quotes, securities
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler


class PortfolioHandler:
    def __init__(self) -> None:
        self._lgr = logging.getLogger()

    async def __call__(self, ctx: handler.Ctx, msg: handler.QuotesUpdated) -> handler.PortfolioUpdated:
        port = await ctx.get_for_update(portfolio.Portfolio)

        old_day = port.day
        old_value = port.value
        old_forecast_days = port.forecast_days

        sec_cache = await self._prepare_sec_cache(ctx, msg.day, port.forecast_days)
        min_turnover = _calc_min_turnover(port, sec_cache)

        self._update_existing_positions(port, sec_cache, min_turnover)
        self._add_new_liquid(port, sec_cache, min_turnover)
        port.update_forecast_days(msg.trading_days)

        if old_forecast_days != port.forecast_days:
            self._lgr.warning("Forecast days changed - %d -> %d", old_forecast_days, port.forecast_days)

        if old_value and old_day != port.day:
            new_value = port.value
            change = new_value / old_value - 1
            self._lgr.warning(f"Portfolio value changed {change:.2%} - {old_value:_.0f} -> {new_value:_.0f}")

        return handler.PortfolioUpdated(trading_days=msg.trading_days)

    async def _prepare_sec_cache(
        self,
        ctx: handler.Ctx,
        update_day: domain.Day,
        forecast_days: int,
    ) -> dict[domain.Ticker, portfolio.Position]:
        async with asyncio.TaskGroup() as tg:
            sec_task = tg.create_task(ctx.get(securities.Securities))
            evolution_task = tg.create_task(ctx.get(evolve.Evolution))

        sec_table = await sec_task
        evolution = await evolution_task

        async with asyncio.TaskGroup() as tg:
            quotes_tasks = [tg.create_task(ctx.get(quotes.Quotes, domain.UID(sec.ticker))) for sec in sec_table.df]

        return {
            sec.ticker: portfolio.Position(
                ticker=sec.ticker,
                lot=sec.lot,
                price=quotes.result().df[-1].close,
                turnover=statistics.median(quote.turnover for quote in quotes.result().df[-forecast_days:]),
            )
            for sec, quotes in zip(sec_table.df, quotes_tasks, strict=True)
            if len(quotes.result().df) > evolution.minimal_returns_days and quotes.result().df[-1].day == update_day
        }

    def _update_existing_positions(
        self,
        port: portfolio.Portfolio,
        sec_cache: dict[domain.Ticker, portfolio.Position],
        min_turnover: float,
    ) -> None:
        updated_positions: list[portfolio.Position] = []

        for position in port.positions:
            match sec_cache.pop(position.ticker, None):
                case None if not position.accounts:
                    self._lgr.warning("Not enough traded %s is removed", position.ticker)
                case None:
                    position.turnover = 0
                    updated_positions.append(position)
                    self._lgr.warning("Not enough traded %s is not removed", position.ticker)
                case new_position if new_position.turnover < min_turnover and not position.accounts:
                    self._lgr.warning("Not liquid %s is removed", position.ticker)
                case new_position if new_position.turnover < min_turnover:
                    new_position.accounts = position.accounts
                    updated_positions.append(new_position)
                    self._lgr.warning("Not liquid %s is not removed", position.ticker)
                case new_position:
                    new_position.accounts = position.accounts
                    updated_positions.append(new_position)

        port.positions = updated_positions

    def _add_new_liquid(
        self,
        port: portfolio.Portfolio,
        sec_cache: dict[domain.Ticker, portfolio.Position],
        min_turnover: float,
    ) -> None:
        for ticker, position in sec_cache.items():
            if position.turnover > min_turnover:
                n, _ = port.find_position(position.ticker)
                port.positions.insert(n, position)
                if port.ver:
                    self._lgr.warning("%s is added", ticker)


def _calc_min_turnover(
    port: portfolio.Portfolio,
    sec_cache: dict[domain.Ticker, portfolio.Position],
) -> float:
    min_turnover = sum(port.cash.values())
    for position in port.positions:
        price = position.price
        if new_position := sec_cache.get(position.ticker):
            price = new_position.price

        min_turnover = max(min_turnover, sum(position.accounts.values()) * price)

    return min_turnover
