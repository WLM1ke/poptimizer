import asyncio
import logging
from typing import TYPE_CHECKING, Final

from aiohttp import abc, web

from poptimizer.controllers.bus import msg
from poptimizer.views.web.web import App

if TYPE_CHECKING:
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


async def run(lgr: logging.Logger, url: HttpUrl, bus: msg.Bus) -> None:
    runner = web.AppRunner(
        App(bus),
        handle_signals=False,
        access_log_class=_AccessLogger,
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        url.host,
        url.port,
    )

    await site.start()

    lgr.info("Server started on %s - press CTRL+C to quit", url)

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        await runner.cleanup()
        lgr.info("Server shutdown finished")
