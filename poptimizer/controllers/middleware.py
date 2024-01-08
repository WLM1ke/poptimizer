from aiohttp import web
from aiohttp.typedefs import Handler
from pydantic import ValidationError

from poptimizer.core import errors


@web.middleware
async def error(
    request: web.Request,
    handler: Handler,
) -> web.StreamResponse:
    try:
        return await handler(request)
    except (errors.InputOutputError, errors.AdaptersError) as err:
        raise web.HTTPInternalServerError(text=str(err)) from err
    except (ValidationError, errors.DomainError) as err:
        raise web.HTTPBadRequest(text=str(err)) from err
