import asyncio
import contextlib
import logging
from datetime import timedelta
from email.message import EmailMessage
from types import TracebackType
from typing import Final, Self

import aiosmtplib

LOGGER_NAME: Final = "Gmail"
_HOST: Final = "smtp.gmail.com"
_PORT: Final = 465
_MAILS_PER_DAY: Final = 500
_FLUSH_DELAY: Final = (timedelta(hours=24) / _MAILS_PER_DAY).total_seconds()
_SUBJECT: Final = "POptimizer"


class Sender:
    def __init__(self, email: str, password: str) -> None:
        self._task: asyncio.Task[None] | None = None
        self._email = email
        self._password = password

        self._buffer: list[str] = []
        self._lock = asyncio.Lock()
        self._lgr = logging.getLogger(name=LOGGER_NAME)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

        await self._send_buffer()

    def send(self, message: str) -> None:
        self._buffer.append(message)
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._flush())

    async def _flush(self) -> None:
        await asyncio.sleep(_FLUSH_DELAY)
        async with self._lock:
            await self._send_buffer()

    async def _send_buffer(self) -> None:
        current_batch = self._buffer
        self._buffer = []

        if not current_batch:
            return

        try:
            await aiosmtplib.send(
                self._build_msg(current_batch),
                hostname=_HOST,
                port=_PORT,
                use_tls=True,
                username=self._email,
                password=self._password,
            )
        except aiosmtplib.SMTPException as err:
            self._lgr.warning("can't send email - %s", err)

            self._buffer = current_batch + self._buffer

    def _build_msg(self, buffer: list[str]) -> EmailMessage:
        messages = "\n".join(buffer)

        msg = EmailMessage()
        msg["Subject"] = _SUBJECT
        msg["From"] = self._email
        msg["To"] = self._email
        msg.set_content(messages)

        return msg
