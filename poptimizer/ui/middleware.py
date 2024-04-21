from aiohttp import abc, typedefs, web
from pydantic import ValidationError

from poptimizer.core import domain, errors


class AccessLogger(abc.AbstractAccessLogger):
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


@web.middleware
class RequestErrorMiddleware:
    def __init__(self, ctx: domain.Ctx) -> None:
        self._ctx = ctx

    async def __call__(
        self,
        request: web.Request,
        handler: typedefs.Handler,
    ) -> web.StreamResponse:
        try:
            return await handler(request)
        except (errors.InputOutputError, errors.AdaptersError) as err:
            self._ctx.warn(f"{err}")

            raise web.HTTPInternalServerError(text=f"{err.__class__.__name__}: {",".join(err.args)}") from err
        except errors.DomainError as err:
            self._ctx.warn(f"{err}")

            raise web.HTTPBadRequest(text=f"{err.__class__.__name__}: {",".join(err.args)}") from err
        except ValidationError as err:
            msg = ",".join(desc["msg"] for desc in err.errors())
            self._ctx.warn(msg=f"{err.__class__.__name__}({msg})")

            raise web.HTTPBadRequest(text=f"{err.__class__.__name__}: {msg}") from err
