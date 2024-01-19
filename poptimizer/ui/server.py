import asyncio

from aiohttp import abc, typedefs, web
from pydantic import HttpUrl, ValidationError

from poptimizer.core import domain, errors
from poptimizer.ui import frontend, portfolio


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
    def __init__(self, ctx: domain.SrvCtx) -> None:
        self._ctx = ctx

    async def __call__(
        self,
        request: web.Request,
        handler: typedefs.Handler,
    ) -> web.StreamResponse:
        try:
            return await handler(request)
        except (errors.InputOutputError, errors.AdaptersError) as err:
            self._ctx.publish(domain.WarningEvent(component=domain.get_component_name(self), msg=f"{err}"))
            raise web.HTTPInternalServerError(text=f"{err.__class__.__name__}: {",".join(err.args)}") from err
        except errors.DomainError as err:
            self._ctx.publish(domain.WarningEvent(component=domain.get_component_name(self), msg=f"{err}"))
            raise web.HTTPBadRequest(text=f"{err.__class__.__name__}: {",".join(err.args)}") from err
        except ValidationError as err:
            self._ctx.publish(domain.WarningEvent(component=domain.get_component_name(self), msg=f"{err}"))
            msg = ",".join(desc["msg"] for desc in err.errors())
            raise web.HTTPBadRequest(text=f"{err.__class__.__name__}: {msg}") from err


class ServerStatusChanged(domain.Event):
    status: str


class APIServerService:
    def __init__(
        self,
        url: HttpUrl,
    ) -> None:
        self._url = url

    async def run(self, ctx: domain.SrvCtx) -> None:
        aiohttp_app = self._prepare_app(ctx)

        runner = web.AppRunner(
            aiohttp_app,
            handle_signals=False,
            access_log_class=AccessLogger,
        )
        await runner.setup()
        site = web.TCPSite(
            runner,
            self._url.host,
            self._url.port,
        )

        await site.start()

        ctx.publish(ServerStatusChanged(status=f"started on {self._url} - press CTRL+C to quit"))

        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            await runner.cleanup()
            ctx.publish(ServerStatusChanged(status="shutdown completed"))

    def _prepare_app(self, ctx: domain.SrvCtx) -> web.Application:
        api = web.Application()
        portfolio.Views(api, ctx)

        app = web.Application(middlewares=[RequestErrorMiddleware(ctx)])
        app.add_subapp("/api/", api)
        frontend.Views(app)

        return app
