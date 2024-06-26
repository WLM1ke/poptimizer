import asyncio

from aiohttp import abc, web
from pydantic import HttpUrl

from poptimizer.service.common import logging


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
    kilo = 2**10

    for unit in ("b", "kb", "Mb", "Gb"):
        if size < kilo:
            return f"{size:.0f}{unit}"

        size /= kilo

    return f"{size:.0f}Tb"


class Server:
    def __init__(self, logging_service: logging.Service, handlers: web.Application, url: HttpUrl) -> None:
        self._logging_service = logging_service
        self._handlers = handlers
        self._url = url

    async def __call__(self) -> None:
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

        self._logging_service.info(f"Server started on {self._url} - press CTRL+C to quit")

        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            await runner.cleanup()
            self._logging_service.info("Server shutdown completed")
