"""Сервис обновления данных."""
import asyncio
import logging
import zoneinfo
from datetime import datetime, timedelta
from typing import Final

from poptimizer.data import backup, domain, exceptions
from poptimizer.data.update import check_raw, cpi, indexes, securities, status, trading_date

_BACKUP_COLLECTIONS: Final = (domain.Group.SECURITIES.value, domain.Group.RAW_DIV.value)

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
_END_HOUR: Final = 0
_END_MINUTE: Final = 45

_CHECK_INTERVAL: Final = timedelta(minutes=1)
_DATE_FORMAT: Final = "%Y-%m-%d"


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
        day=now.day,
    ) - timedelta(days=delta)


class Updater:
    """Сервис обновления данных."""

    def __init__(  # noqa: WPS211
        self,
        backup_srv: backup.Service,
        date_srv: trading_date.Service,
        cpi_srv: cpi.Service,
        indexes_srv: indexes.Service,
        securities_srv: securities.Service,
        status_srv: status.Service,
        check_raw_srv: check_raw.Service,
    ) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)

        self._backup_srv = backup_srv

        self._date_srv = date_srv

        self._cpi_srv = cpi_srv
        self._indexes_srv = indexes_srv

        self._securities_srv = securities_srv
        self._status_srv = status_srv
        self._check_raw_srv = check_raw_srv

        self._checked_day = datetime.fromtimestamp(0)

    async def run(self, stop_event: asyncio.Event) -> None:
        """Запускает регулярное обновление данных."""
        await self._init_run()

        while not stop_event.is_set():
            try:
                await self._try_to_update()
            except exceptions.DataError as err:
                self._logger.warning(f"can't complete update {err}")

            aws = (stop_event.wait(),)
            await asyncio.wait(
                aws,
                timeout=_CHECK_INTERVAL.total_seconds(),
                return_when=asyncio.FIRST_COMPLETED,
            )

        self._logger.info(f"stopped with last update for {self._checked_day:{_DATE_FORMAT}}")

    async def _init_run(self) -> None:
        await self._backup_srv.restore(_BACKUP_COLLECTIONS)

        try:
            self._checked_day = await self._date_srv.get_last_date()
        except exceptions.DataError as err:
            raise exceptions.DataError("can't init update process") from err
        self._logger.info(f"started with last update for {self._checked_day:{_DATE_FORMAT}}")

    async def _try_to_update(self) -> None:
        last_day = _last_day()

        if self._checked_day >= last_day:
            return

        self._logger.info(f"{last_day:{_DATE_FORMAT}} ended - checking new trading day")

        new_update_day = await self._date_srv.update(self._checked_day)

        if new_update_day <= self._checked_day:
            self._checked_day = last_day
            self._logger.info("update not required")

            return

        self._logger.info("beginning updates")

        await self._update(new_update_day)

        self._checked_day = last_day
        self._logger.info("updates are completed")

    async def _update(self, update_day: datetime) -> None:
        await asyncio.gather(
            self._cpi_srv.update(update_day),
            self._indexes_srv.update(update_day),
            self._update_sec(update_day),
        )

        await self._backup_srv.backup(_BACKUP_COLLECTIONS)

    async def _update_sec(self, update_day: datetime) -> None:
        sec = await self._securities_srv.update(update_day)
        await self._update_raw_div(update_day, sec)

    async def _update_raw_div(self, update_day: datetime, sec: list[securities.Security]) -> None:
        status_rows = await self._status_srv.update(update_day, sec)
        await self._check_raw_srv.check(status_rows)
