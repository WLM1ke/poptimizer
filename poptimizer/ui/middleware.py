from aiohttp import typedefs, web
from pydantic import ValidationError

from poptimizer.adapter import telegram
from poptimizer.core import errors


@web.middleware
class RequestErrorMiddleware:
    def __init__(self, telegram_logger: telegram.Logger) -> None:
        self._lgr = telegram_logger

    async def __call__(
        self,
        request: web.Request,
        handler: typedefs.Handler,
    ) -> web.StreamResponse:
        try:
            return await handler(request)
        except (errors.InputOutputError, errors.AdaptersError) as err:
            self._lgr.warning(f"{err}")

            raise web.HTTPInternalServerError(text=f"{err.__class__.__name__}: {",".join(err.args)}") from err
        except errors.DomainError as err:
            self._lgr.warning(f"{err}")

            raise web.HTTPBadRequest(text=f"{err.__class__.__name__}: {",".join(err.args)}") from err
        except ValidationError as err:
            msg = ",".join(desc["msg"] for desc in err.errors())
            self._lgr.warning(msg=f"{err.__class__.__name__}({msg})")

            raise web.HTTPBadRequest(text=f"{err.__class__.__name__}: {msg}") from err
