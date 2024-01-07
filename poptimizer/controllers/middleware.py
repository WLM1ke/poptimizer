from typing import Protocol

from aiohttp import web
from aiohttp.typedefs import Handler
from pydantic import ValidationError

from poptimizer.core import domain, errors


class Requester(Protocol):
    async def request[Res: domain.Response](self, request: domain.Request[Res]) -> Res:
        ...


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
