import http
from datetime import timedelta
from pathlib import Path
from typing import Final

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape

from poptimizer.views.web import models

_YEAR_IN_SECONDS: Final = int(timedelta(days=365).total_seconds())


def format_float(number: float, decimals: int | None = None) -> str:
    match decimals:
        case None if number % 1:
            rez = f"{number:_}"
        case None:
            rez = f"{int(number):_}"
        case _:
            rez = f"{number:_.{decimals}f}"

    return rez.replace("_", " ").replace(".", ",")


def format_percent(number: float) -> str:
    return f"{format_float(number * 100, 1)} %"


def _with_cookie(resp: web.Response, cookie: models.Cookie | None) -> web.Response:
    if cookie:
        for name, value in cookie:
            resp.set_cookie(
                name,
                value,
                max_age=_YEAR_IN_SECONDS,
                httponly=True,
                samesite="Lax",
            )

    return resp


class View:
    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=select_autoescape(["html"]),
        )

    def render_page(self, layout: models.Layout, main: models.BaseModel, *, first_load: bool) -> web.StreamResponse:
        match first_load:
            case True:
                template = "index.html"
            case False:
                template = "body.html"

        return web.Response(
            text=self._env.get_template(template).render(
                layout=layout,
                main=main,
                format_float=format_float,
                format_percent=format_percent,
            ),
            content_type="text/html",
        )

    def set_cookie(self, cookie: models.Cookie) -> web.StreamResponse:
        return _with_cookie(web.Response(status=http.HTTPStatus.NO_CONTENT), cookie)

    def render_theme(self, cookie: models.Cookie) -> web.StreamResponse:
        return _with_cookie(
            web.Response(
                text=self._env.get_template(f"theme/{cookie.theme}.html").render(),
                content_type="text/html",
            ),
            cookie,
        )

    def render_main(
        self,
        main: models.BasePage,
        cookie: models.Cookie | None = None,
    ) -> web.StreamResponse:
        return _with_cookie(
            web.Response(
                text=self._env.get_template(f"main/{main.page}.html").render(
                    main=main,
                    format_float=format_float,
                    format_percent=format_percent,
                ),
                content_type="text/html",
            ),
            cookie,
        )

    def render_alert(self, code: int, alert: str) -> web.Response:
        return web.Response(
            status=code,
            text=self._env.get_template("components/alert.html").render(alert=alert),
            content_type="text/html",
        )
