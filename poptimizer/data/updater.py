"""Сервис обновления данных."""
import asyncio
import logging
import zoneinfo
from datetime import datetime, timedelta
from typing import Final, Protocol

from poptimizer.core import backup, domain
from poptimizer.data import exceptions
from poptimizer.data.update import cpi, divs, indexes, quotes, securities, trading_date, usd
from poptimizer.data.update.raw import check_raw, nasdaq, reestry, status

_BACKUP_COLLECTIONS: Final = (domain.Group.RAW_DIV,)

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
_END_HOUR: Final = 0
_END_MINUTE: Final = 45

_CHECK_INTERVAL: Final = timedelta(minutes=1)
_BACK_OFF_FACTOR: Final = 2

_DATE_FORMAT: Final = "%Y-%m-%d"


class UpdateStep(Protocol):
    """Служба, отвечающая за обновление."""

    async def update(self, update_day: datetime) -> None:
        """Запуск обновления."""


class Updater:
    """Сервис обновления данных."""

    def __init__(  # noqa: WPS211
        self,
        backup_srv: backup.Service,
        date_srv: trading_date.Service,
        cpi_srv: cpi.Service,
        indexes_srv: indexes.Service,
        securities_srv: securities.Service,
        quotes_srv: quotes.Service,
        usd_srv: usd.Service,
        dividends_srv: divs.Service,
        status_srv: status.Service,
        reestry_srv: reestry.Service,
        nasdaq_srv: nasdaq.Service,
        check_raw_srv: check_raw.Service,
        externals: list[UpdateStep],
    ) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._factor = 1

        self._backup_srv = backup_srv

        self._date_srv = date_srv

        self._cpi_srv = cpi_srv
        self._indexes_srv = indexes_srv

        self._securities_srv = securities_srv
        self._quotes_srv = quotes_srv
        self._usd_srv = usd_srv
        self._dividends_srv = dividends_srv

        self._status_srv = status_srv
        self._reestry_srv = reestry_srv
        self._nasdaq_srv = nasdaq_srv
        self._check_raw_srv = check_raw_srv

        self._externals = externals

        self._checked_day = datetime.fromtimestamp(0)

    async def run(self, stop_event: asyncio.Event) -> None:
        """Запускает регулярное обновление данных."""
        await self._init_run()

        while not stop_event.is_set():
            try:
                await self._try_to_update()
            except exceptions.DataError as err:
                self._logger.warning(f"can't complete update {err}")
                self._factor *= _BACK_OFF_FACTOR
            else:
                self._factor = 1

            aws = (stop_event.wait(),)
            await asyncio.wait(
                aws,
                timeout=_CHECK_INTERVAL.total_seconds() * self._factor,
                return_when=asyncio.FIRST_COMPLETED,
            )

        self._logger.info(f"shutdown completed with last update for {self._checked_day:{_DATE_FORMAT}}")

    async def _init_run(self) -> None:
        await self._backup_srv.restore(_BACKUP_COLLECTIONS)
        self._checked_day = await self._date_srv.get_date_from_local_store()

        self._logger.info(f"started with last update for {self._checked_day:{_DATE_FORMAT}}")

    async def _try_to_update(self) -> None:
        last_day = _last_day()

        if self._checked_day >= last_day:
            return

        self._logger.info(f"checking new trading data for {last_day:{_DATE_FORMAT}}")

        new_update_day = await self._date_srv.get_date_from_iss()

        if new_update_day <= self._checked_day:
            self._checked_day = last_day
            self._logger.info("update not required")

            return

        self._logger.info("updates are beginning")

        await self._update(new_update_day)

        await self._date_srv.save(new_update_day)

        self._checked_day = last_day
        self._logger.info("updates are completed")

    async def _update(self, update_day: datetime) -> None:
        await asyncio.gather(
            self._cpi_srv.update(update_day),
            self._indexes_srv.update(update_day),
            self._update_sec(update_day),
        )

        await self._backup_srv.backup(_BACKUP_COLLECTIONS)

        for srv in self._externals:
            await srv.update(update_day)

    async def _update_sec(self, update_day: datetime) -> None:
        sec_list, usd_list = await asyncio.gather(
            self._securities_srv.update(update_day),
            self._usd_srv.update(update_day),
        )

        await asyncio.gather(
            self._quotes_srv.update(update_day, sec_list),
            self._dividends_srv.update(update_day, sec_list, usd_list),
            self._update_raw_div(update_day, sec_list),
        )

    async def _update_raw_div(self, update_day: datetime, sec: list[securities.Security]) -> None:
        status_rows = await self._status_srv.update(update_day, sec)

        await asyncio.gather(
            self._reestry_srv.update(update_day, status_rows),
            self._nasdaq_srv.update(update_day, status_rows),
            self._check_raw_srv.check(status_rows),
        )


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
