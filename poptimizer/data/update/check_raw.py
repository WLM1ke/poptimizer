"""Сервис проверки наличия данных по ожидаемым дивидендам."""
import logging

from poptimizer.data import exceptions, repo
from poptimizer.data.edit import dividends
from poptimizer.data.update import status


class Service:
    """Сервис проверки наличия данных по ожидаемым дивидендам."""

    def __init__(self, repository: repo.Repo) -> None:
        self._logger = logging.getLogger("CheckRaw")
        self._repo = repository

    async def check(self, status_rows: list[status.Status]) -> None:
        """Проверяет, что все даты ожидаемых дивидендов имеются во вручную введенных дивидендах."""
        try:
            await self._check(status_rows)
        except exceptions.DataError as err:
            self._logger.warning(f"can't complete check {err}")

            return

        self._logger.info("check is completed")

    async def _check(self, status_rows: list[status.Status]) -> None:
        for row in status_rows:
            table = await self._repo.get(dividends.Table, row.ticker)

            if not table.has_date(row.date):
                date = row.date.date()
                self._logger.warning(f"{row.ticker} missed dividend at {date}")
