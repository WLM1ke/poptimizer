"""Таблица с торговыми датами."""
from datetime import datetime, timedelta, timezone
from typing import ClassVar, Final, List

import pandas as pd

import poptimizer.data_di.ports
from poptimizer.data_di.adapters.gateways import moex
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.tables import base
from poptimizer.shared import domain

# Часовой пояс MOEX
_MOEX_TZ: Final = timezone(timedelta(hours=3))

# Торги заканчиваются в 24.00, но данные публикуются 00.45
_END_HOUR: Final = 0
_END_MINUTE: Final = 45


def _to_utc_naive(date: datetime) -> datetime:
    """Переводит дату в UTC и делает ее наивной."""
    date = date.astimezone(timezone.utc)
    return date.replace(tzinfo=None)


def _trading_day_potential_end() -> datetime:
    """Возможный конец последнего торгового дня UTC."""
    now = datetime.now(_MOEX_TZ)
    end_of_trading = now.replace(
        hour=_END_HOUR,
        minute=_END_MINUTE,
        second=0,
        microsecond=0,
    )
    if end_of_trading > now:
        end_of_trading -= timedelta(days=1)
    return _to_utc_naive(end_of_trading)


class TradingDates(base.AbstractTable[events.AppStarted]):
    """Таблица с данными о торговых днях.

    Обрабатывает событие начала работы приложения.
    Инициирует событие в случае окончания очередного торгового дня.
    """

    group: ClassVar[poptimizer.data_di.ports.GroupName] = poptimizer.data_di.ports.TRADING_DATES
    _gateway: Final = moex.TradingDatesGateway()

    def _update_cond(self, event: events.AppStarted) -> bool:
        """Обновляет, если последняя дата обновления после потенциального окончания торгового дня."""
        if self._timestamp is None:
            return True
        if _trading_day_potential_end() > self._timestamp:
            return True
        return False

    async def _prepare_df(self, event: events.AppStarted) -> pd.DataFrame:
        """Загружает новый DataFrame."""
        return await self._gateway.get()

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Проверка корректности индекса и заголовков."""
        if df_new.index.tolist() != [0]:
            raise base.TableIndexError()
        if df_new.columns.tolist() != ["from", "till"]:
            raise base.TableIndexError()

    def _new_events(self, event: events.AppStarted) -> List[domain.AbstractEvent]:
        """Событие окончания торгового дня."""
        if (df := self._df) is None:
            raise base.TableNeverUpdatedError(self._id)
        last_trading_day = df.loc[0, "till"]
        return [events.TradingDayEnded(last_trading_day.date())]
