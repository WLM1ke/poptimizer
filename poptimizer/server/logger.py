"""Реализует логер в формате aiohttp и middleware для обхода неточности учета времени uvloop."""
import http
import time
from typing import Final

from aiohttp import web
from aiohttp.abc import AbstractAccessLogger
from aiohttp.typedefs import Handler

from poptimizer import lgr

_START_TIME: Final = "start_time"


@web.middleware
async def set_start_time_and_headers(
    request: web.Request,
    handler: Handler,  # noqa: WPS110
) -> web.StreamResponse:
    """Устанавливает время поступления запроса для логирования и заголовок сервера.

    Время начала обработки нужно для логирования, так как при использовании uvloop оно вычисляется с точностью до 1мс.
    Дополнительно устанавливается заголовок сервера.
    """
    request[_START_TIME] = time.monotonic()

    response = await handler(request)

    response.headers["Server"] = "POptimizer"

    return response


class AccessLogger(AbstractAccessLogger):
    """Логирует основные параметры обработки запроса."""

    def log(self, request: web.BaseRequest, response: web.StreamResponse, _: float) -> None:
        """Логирует основные параметры обработки запроса.

        Не используется аргумент времени из AbstractAccessLogger, так как с uvloop он вычисляется с точностью до 1мс.
        Вместо него берется время из заголовка запроса, установленного middleware.

        Сохраняет цветное отображения для консоли и обычное для отправки в Телеграм.
        """
        req_tmpl, req_tmpl_color = _format_request(request)
        time_tmpl = _format_time(request)
        res_tmpl, res_tmpl_color = _format_response(response)

        if response.status < http.HTTPStatus.INTERNAL_SERVER_ERROR:
            self.logger.info(
                f"{req_tmpl} {res_tmpl} {time_tmpl}",
                extra={lgr.COLOR_MSG: f"{req_tmpl_color} {res_tmpl_color} {time_tmpl}"},
            )

            return

        self.logger.warning(
            f"{req_tmpl} {res_tmpl} {time_tmpl}",
            extra={lgr.COLOR_MSG: f"{req_tmpl_color} {res_tmpl_color} {time_tmpl}"},
        )


def _format_request(request: web.BaseRequest) -> tuple[str, str]:
    method = request.method
    path = request.path

    return (
        f"{method} {path}",
        f"\033[1;30m{method}\033[0m {path}",
    )


def _format_response(response: web.StreamResponse) -> tuple[str, str]:
    code, code_color = _status_code(response)
    content_length = _content_length(response)

    return (
        f"{code} {content_length}",
        f"{code_color} {content_length}",
    )


def _status_code(response: web.StreamResponse) -> tuple[str, str]:
    status_code = response.status
    status_phrase = http.HTTPStatus(status_code).phrase

    status_and_phrase = f"{status_code} {status_phrase}"

    tmpl = {
        1: "\033[90m{0}\033[0m",
        2: "\033[32m{0}\033[0m",
        3: "\033[33m{0}\033[0m",
        4: "\033[31m{0}\033[0m",
        5: "\033[1;91m{0}\033[0m",
    }[status_code // 100]

    return status_and_phrase, tmpl.format(status_and_phrase)


def _content_length(response: web.StreamResponse) -> str:
    size = float(response.body_length)
    kilo = 2**10

    if size < kilo:
        return f"{size:.0f}b"
    elif kilo <= size < kilo**2:
        size /= kilo
        unit = "kb"
    else:
        size /= kilo**2
        unit = "Mb"

    return f"{size:.1f}{unit}"


def _format_time(request: web.BaseRequest) -> str:
    resp_time = time.monotonic() - request[_START_TIME]

    milli = 10**-3

    if resp_time < milli:
        unit = "μs"
        resp_time /= milli**2
    elif milli <= resp_time < 1:
        unit = "ms"
        resp_time /= milli
    else:
        unit = "s"

    return f"{resp_time:.1f}{unit}"
