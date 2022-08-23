"""Сервис обновления данных."""
import asyncio
import logging
import zoneinfo
from datetime import datetime, timedelta
from typing import Final

from poptimizer.data.trading_day import DatesSrv

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
_END_HOUR: Final = 0
_END_MINUTE: Final = 45

_CHECK_INTERVAL: Final = timedelta(minutes=1)
_DATE_FORMAT: Final = "%Y-%m-%d"


class Updater:
    """Сервис обновления данных."""

    def __init__(self, dates_srv: DatesSrv) -> None:
        """Первоначально последней датой обновления считается начало эпохи."""
        self._logger = logging.getLogger(self.__class__.__name__)
        self._dates_srv = dates_srv
        self._checked_day = datetime.fromtimestamp(0)

    async def run(self, stop_event: asyncio.Event) -> None:
        """Запускает регулярное обновление данных."""
        self._checked_day = await self._dates_srv.get()
        self._logger.info(f"started with last update for {self._checked_day:{_DATE_FORMAT}}")

        while not stop_event.is_set():
            await self._try_to_update()

            aws = (stop_event.wait(),)
            await asyncio.wait(
                aws,
                timeout=_CHECK_INTERVAL.total_seconds(),
                return_when=asyncio.FIRST_COMPLETED,
            )

        self._logger.info(f"stopped with last update for {self._checked_day:{_DATE_FORMAT}}")

    async def _try_to_update(self) -> None:
        last_day = _last_day()

        if self._checked_day >= last_day:
            return

        self._logger.info(f"{last_day:{_DATE_FORMAT}} ended - checking new trading day")

        if (new_update_day := await self._dates_srv.update(self._checked_day)) is None:
            self._logger.warning("can't check new trading day")

            return

        if new_update_day <= self._checked_day:
            self._checked_day = last_day
            self._logger.info("update not required")

            return

        self._logger.info("beginning updates")
        # TODO запуск обновления

        self._checked_day = last_day
        self._logger.info("updates are finished")


def _last_day() -> datetime:
    now = datetime.now(_MOEX_TZ)
    end_of_trading = now.replace(
        hour=_END_HOUR,
        minute=_END_MINUTE,
        second=0,
        microsecond=0,
        tzinfo=_MOEX_TZ,
    )

    delta = 2
    if end_of_trading < now:
        delta = 1

    return datetime(
        year=now.year,
        month=now.month,
        day=now.day - delta,
    )
