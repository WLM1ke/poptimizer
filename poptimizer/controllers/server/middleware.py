import logging

from aiohttp import typedefs, web
from pydantic import ValidationError

from poptimizer import errors


@web.middleware
class RequestErrorMiddleware:
    def __init__(self) -> None:
        self._lgr = logging.getLogger()

    async def __call__(self, request: web.Request, handler: typedefs.Handler) -> web.StreamResponse:
        try:
            return await handler(request)
        except (errors.AdapterError, errors.ControllersError) as err:
            self._lgr.warning("Can't handle request - %s", err)

            raise web.HTTPInternalServerError(text=f"{err.__class__.__name__}: {','.join(err.args)}") from err
        except (errors.DomainError, errors.UseCasesError) as err:
            self._lgr.warning("Can't handle request - %s", err)

            raise web.HTTPBadRequest(text=f"{err.__class__.__name__}: {','.join(err.args)}") from err
        except ValidationError as err:
            self._lgr.warning("Can't handle request - %s", err)
            msg = ",".join(desc["msg"] for desc in err.errors())

            raise web.HTTPBadRequest(text=f"{err.__class__.__name__}: {msg}") from err
