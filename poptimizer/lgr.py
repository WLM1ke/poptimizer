"""Настройки логирования."""
import asyncio
import logging
import sys
import types
from typing import Final, Literal

import aiohttp

TELEGRAM_TASK: Final = "Telegram"


class ColorFormatter(logging.Formatter):
    """Цветное логирование."""

    levels: Final = types.MappingProxyType(
        {
            logging.DEBUG: "\033[90mDBG\033[0m",
            logging.INFO: "\033[34mINF\033[0m",
            logging.WARNING: "\033[31mWRN\033[0m",
            logging.ERROR: "\033[1;31mERR\033[0m",
            logging.CRITICAL: "\033[1;91mCRT\033[0m",
        },
    )

    def __init__(
        self,
        fmt: str = "{asctime} {levelname} {name}: {message}",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        style: Literal["%", "{", "$"] = "{",
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def format(self, record: logging.LogRecord) -> str:
        """Подменяет отображение уровня логирования цветным аналогом."""
        record.levelname = self.levels[record.levelno]

        return super().format(record)


class AsyncTelegramHandler(logging.Handler):
    """Отправляет сообщения уровня WARNING и выше в Телеграм.

    При этом исключаются сообщения самого обработчика, чтобы не вызвать рекурсивную отправку в случае ошибки в работе.
    Использует асинхронную отправку, поэтому должен использоваться после запуска eventloop.
    """

    def __init__(self, session: aiohttp.ClientSession, token: str, chat_id: str) -> None:
        super().__init__(level=logging.WARNING)

        formatter = logging.Formatter(
            fmt="<strong>{name}</strong>\n{message}",
            style="{",
        )
        self.setFormatter(formatter)
        self.addFilter(lambda record: record.name != "Telegram")

        self._logger = logging.getLogger("Telegram")
        self._session = session
        self._url = f"https://api.telegram.org/bot{token}/SendMessage"
        self._chat_id = chat_id
        self._tasks: set[asyncio.Task[None]] = set()

    def emit(self, record: logging.LogRecord) -> None:
        """Выполняет асинхронную отправку сообщения в Телеграм.

        Создаваемые асинхронные задачи имеют только weak references. Поэтому на них необходимо создавать полноценные
        ссылки и после выполнения их удалять, для обеспечения корректной работы garbage-collector.

        https://docs.python.org/3/library/asyncio-task.html#creating-tasks
        """
        task = asyncio.create_task(self._send(record), name=TELEGRAM_TASK)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _send(self, record: logging.LogRecord) -> None:
        """https://core.telegram.org/bots/api#sendmessage."""
        json = {
            "chat_id": self._chat_id,
            "parse_mode": "HTML",
            "text": self.format(record),
        }

        async with self._session.post(self._url, json=json) as resp:
            if not resp.ok:
                err_desc = await resp.json()
                self._logger.warning(f"can't send {err_desc}")


def config(session: aiohttp.ClientSession, token: str, chat_id: str, level: int = logging.INFO) -> None:
    """Настраивает логирование в stdout, а для уровней WARNING и выше в Телеграм."""
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(ColorFormatter())

    logging.basicConfig(
        level=level,
        handlers=[stream_handler, AsyncTelegramHandler(session, token, chat_id)],
    )
