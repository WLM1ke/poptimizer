from aiohttp import typedefs, web
from pydantic import ValidationError

from poptimizer.adapter import adapter
from poptimizer.domain import consts
from poptimizer.service.common import logging, service


@web.middleware
class RequestErrorMiddleware:
    def __init__(self, logging_service: logging.Service) -> None:
        self._logging_service = logging_service

    async def __call__(
        self,
        request: web.Request,
        handler: typedefs.Handler,
    ) -> web.StreamResponse:
        try:
            return await handler(request)
        except (adapter.AdaptersError, service.ServiceError) as err:
            self._logging_service.warn(f"{err}")

            raise web.HTTPInternalServerError(text=f"{err.__class__.__name__}: {",".join(err.args)}") from err
        except consts.DomainError as err:
            self._logging_service.warn(f"{err}")

            raise web.HTTPBadRequest(text=f"{err.__class__.__name__}: {",".join(err.args)}") from err
        except ValidationError as err:
            msg = ",".join(desc["msg"] for desc in err.errors())
            self._logging_service.warn(msg=f"{err.__class__.__name__}({msg})")

            raise web.HTTPBadRequest(text=f"{err.__class__.__name__}: {msg}") from err
