"""Сервис обновления данных."""
import asyncio
import logging
import zoneinfo
from typing import Final

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
_END_HOUR: Final = 0
_END_MINUTE: Final = 45


class Updater:
    """Сервис обновления данных."""

    def __init__(self) -> None:
        self._logger = logging.getLogger("Updater")

    async def run(self, stop_event: asyncio.Event) -> None:
        """Запускает регулярное обновление данных."""
        while not stop_event.is_set():
            self._logger.info("running")
            time_to_update = 10
            aws = (stop_event.wait(), )
            await asyncio.wait(
                aws,
                timeout=time_to_update,
                return_when=asyncio.FIRST_COMPLETED,
            )
