"""Таблица с торгуемыми бумагами."""
import asyncio
from typing import Callable, ClassVar, Final

import pandas as pd

from poptimizer import config
from poptimizer.data import ports
from poptimizer.data.adapters.gateways import moex
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base
from poptimizer.shared import col, domain

# Параметры проверки обыкновенная акция или привилегированная
COMMON_TICKER_LENGTH: Final = 4
PREFERRED_TICKER_ENDING: Final = "P"


class WrongTickerTypeError(config.POptimizerError):
    """Некорректный тикер."""


def _ticker_type(sec_type: str) -> int:
    """Является ли акция обыкновенной."""
    try:
        return {
            "1": col.ORDINARY,
            "2": col.PREFERRED,
            "D": col.ORDINARY,
        }[sec_type]
    except KeyError as err:
        raise WrongTickerTypeError from err


# Перечень рынков и режимов торгов, для которых загружаются списки доступных бумаг
MARKETS_BOARDS: Final = (
    ("shares", "TQBR", _ticker_type),
    ("shares", "TQTF", lambda _: col.ETF),
)


class Securities(base.AbstractTable[events.USDUpdated]):
    """Таблица с данными о торгуемых бумагах.

    Обрабатывает событие об окончании торгового дня.
    Инициирует события о торговле конкретными бумагами для трех режимов торгов.
    """

    group: ClassVar[ports.GroupName] = ports.SECURITIES
    _gateway: Final = moex.SecuritiesGateway()

    def _update_cond(self, event: events.USDUpdated) -> bool:
        """Если торговый день окончился, то обязательно требуется обновление."""
        return True

    async def _prepare_df(self, event: events.USDUpdated) -> pd.DataFrame:
        """Загружает новый DataFrame."""
        aws = [self._load_and_format_df(*market_board) for market_board in MARKETS_BOARDS]
        dfs = await asyncio.gather(*aws)
        df_all = pd.concat(dfs, axis=0)
        return df_all.sort_index(axis=0)

    async def _load_and_format_df(
        self,
        market: str,
        board: str,
        type_func: Callable[[str], int],
    ) -> pd.DataFrame:
        """Загружает данные о торгуемых бумагах и добавляет информацию о рынке."""
        df = await self._gateway(market=market, board=board)
        df[col.MARKET] = market
        df[col.TICKER_TYPE] = df[col.TICKER_TYPE].apply(type_func)

        return df

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        base.check_unique_increasing_index(df_new)

    def _new_events(self, event: events.USDUpdated) -> list[domain.AbstractEvent]:
        """События факта торговли конкретных бумаг."""
        df: pd.DataFrame = self._df
        trading_date = event.date

        return [
            events.TickerTraded(
                ticker,
                df.at[ticker, col.ISIN],
                df.at[ticker, col.MARKET],
                trading_date,
                event.usd.copy(deep=True),
            )
            for ticker in df.index
        ]
