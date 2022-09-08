"""Middleware для перехвата ошибок и исправления низкой точности времени uvloop для логирования."""
import logging
import time
from typing import Final

from aiohttp import web
from aiohttp.typedefs import Handler
from pydantic import ValidationError

from poptimizer.data import exceptions
from poptimizer.exceptions import POError
from poptimizer.server import logger

_LOGGER: Final = logging.getLogger("Server")


@web.middleware
async def set_start_time_and_headers(
    request: web.Request,
    handler: Handler,  # noqa: WPS110
) -> web.StreamResponse:
    """Устанавливает время поступления запроса для логирования и заголовок сервера.

    Время начала обработки нужно для логирования, так как при использовании uvloop оно вычисляется с точностью до 1мс.
    Дополнительно устанавливается заголовок сервера.
    """
    request[logger.START_TIME] = time.monotonic()

    response = await handler(request)

    response.headers["Server"] = "POptimizer"

    return response


@web.middleware
async def error(
    request: web.Request,
    handler: Handler,  # noqa: WPS110
) -> web.StreamResponse:
    """Преобразует ошибки web.HTTPBadRequest для пользовательских ошибок и web.HTTPInternalServerError для остальных."""
    try:
        return await handler(request)
    except web.HTTPException:  # noqa: WPS329
        raise
    except (ValidationError, exceptions.EditError) as err:
        raise web.HTTPBadRequest(text=str(err))
    except BaseException as err:  # noqa: WPS424
        err_text = repr(err)
        if isinstance(err, POError):
            err_text = str(err)

        _LOGGER.exception(f"internal error while handling request -> {err_text}")

        raise web.HTTPInternalServerError
