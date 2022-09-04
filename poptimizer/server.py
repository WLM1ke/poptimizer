"""Создает сервер со всеми обработчиками."""
import http
import logging
import time

import uvicorn
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from poptimizer.data.edit import select


class LoggingMiddleware(BaseHTTPMiddleware):
    """Осуществляет логирование запросов."""

    def __init__(self, app: ASGIApp, logger: logging.Logger):
        super().__init__(app)
        self._logger = logger

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:  # noqa: WPS210
        """Логирует основные параметры запроса."""
        host = getattr(request.client, "host", "")
        port = getattr(request.client, "port", "")
        method = request.method
        path = request.url.path

        start = time.monotonic()
        response = await call_next(request)
        timer = _format_time(time.monotonic() - start)

        status_code = _status_code_colored(response.status_code)
        content_length = _get_content_length(response)

        logger = self._logger.info
        if response.status_code >= http.HTTPStatus.INTERNAL_SERVER_ERROR:
            logger = self._logger.warning

        logger(
            f"{host}:{port} - \033[1;30m{method} {path}\033[0m {status_code} {content_length} {timer}",  # noqa: WPS221
        )

        return response


def _status_code_colored(status_code: int) -> str:
    status_phrase = http.HTTPStatus(status_code).phrase

    status_and_phrase = f"{status_code} {status_phrase}"

    tmpl = {
        1: "\033[90m{0}\033[0m",
        2: "\033[32m{0}\033[0m",
        3: "\033[33m{0}\033[0m",
        4: "\033[31m{0}\033[0m",
        5: "\033[1;91m{0}\033[0m",
    }[status_code // 100]

    return tmpl.format(status_and_phrase)


def _get_content_length(response: Response) -> str:
    size = float(response.headers["content-length"])

    if size < 1024:
        return f"{size}b"

    size /= 1024

    if size < 1024:
        unit = "kb"
    else:
        size /= 1024
        unit = "Mb"

    return f"{size:.1f}{unit}"


def _format_time(resp_time: float) -> str:
    unit = "s"
    mul = 1

    if resp_time < 10**-3:
        unit = "μs"
        mul = 10**6
    elif resp_time < 1:
        mul = 10**3
        unit = "ms"

    resp_time *= mul

    return f"{resp_time:.1f}{unit}"


def create(host: str, port: int) -> uvicorn.Server:
    """Создает сервер со всеми обработчиками.

    Обнулен конфиг логов для сервера, чтобы использовался единообразный подход с другими сервисами.
    Отключено логирование запросов у сервера, и сделано на уровне FastAPI.
    """
    app = FastAPI()
    app.include_router(select.router)
    app.add_middleware(LoggingMiddleware, logger=logging.getLogger("Server"))

    u_cfg = uvicorn.Config(
        app,
        host=host,
        port=port,
        use_colors=True,
        log_config=None,
        access_log=False,
        server_header=False,
        headers=[("Server", "POptimizer")],
    )

    return uvicorn.Server(u_cfg)
