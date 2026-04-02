import asyncio
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
        self._email = email
        self._password = password
        self._buffer = list[str]()
        self._not_empty = asyncio.Event()
        self._lgr = logging.getLogger(name=LOGGER_NAME)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._buffer:
            await self._send(self._build_msg(self._buffer))

    def send(self, message: str) -> None:
        self._buffer.append(message)
        self._not_empty.set()

    async def run(self) -> None:
        while await self._not_empty.wait():
            await asyncio.sleep(_FLUSH_DELAY)
            self._not_empty.clear()

            current_buffer = self._buffer[:]
            self._buffer.clear()

            try:
                if not await self._send(self._build_msg(current_buffer)):
                    self._buffer = current_buffer + self._buffer
            except asyncio.CancelledError:
                self._buffer = current_buffer + self._buffer

                return

    async def _send(self, msg: EmailMessage) -> bool:
        try:
            await aiosmtplib.send(
                msg,
                hostname=_HOST,
                port=_PORT,
                use_tls=True,
                username=self._email,
                password=self._password,
            )
        except aiosmtplib.SMTPException as err:
            self._lgr.warning("Can't send email: %s", err)

            return False
        else:
            return True

    def _build_msg(self, messages: list[str]) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = _SUBJECT
        msg["From"] = self._email
        msg["To"] = self._email
        msg.set_content("\n".join(messages))

        return msg
