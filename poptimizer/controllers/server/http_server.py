import asyncio
import logging
from typing import Final

from aiohttp import abc, web
from pydantic import HttpUrl

_KILOBYTE: Final = 2**10


class _AccessLogger(abc.AbstractAccessLogger):
    def log(self, request: web.BaseRequest, response: web.StreamResponse, time: float) -> None:
        self.logger.info(
            "%s %s %d %s %dms",
            request.method,
            request.path_qs,
            response.status,
            _content_length(response),
            int(time * 1000),
        )


def _content_length(response: web.StreamResponse) -> str:
    size = response.body_length

    for unit in ("b", "kb", "Mb", "Gb"):
        if size < _KILOBYTE:
            return f"{size:.0f}{unit}"

        size /= _KILOBYTE

    return f"{size:.0f}Tb"


class Server:
    def __init__(self, handlers: web.Application, url: HttpUrl) -> None:
        self._lgr = logging.getLogger()
        self._handlers = handlers
        self._url = url

    async def run(self) -> None:
        runner = web.AppRunner(
            self._handlers,
            handle_signals=False,
            access_log_class=_AccessLogger,
        )
        await runner.setup()
        site = web.TCPSite(
            runner,
            self._url.host,
            self._url.port,
        )

        await site.start()

        self._lgr.info("Server started on %s - press CTRL+C to quit", self._url)

        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            await runner.cleanup()
            self._lgr.info("Server shutdown finished")
