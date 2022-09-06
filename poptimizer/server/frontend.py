"""Ручки для выдачи статики SPA Frontend."""
from pathlib import Path
from typing import Final

from aiohttp import web

_STATIC: Final = Path(__file__).parents[2] / "static"
_INDEX_PAGE: Final = _STATIC / "index.html"


async def index(_: web.Request) -> web.StreamResponse:
    """Главная страничка приложения."""
    return web.FileResponse(_INDEX_PAGE)


def add(app: web.Application) -> None:
    """Добавляет ручки для выдачи статики Frontend."""
    app.add_routes(
        [
            web.get("/", index),
            web.static("/", _STATIC),
        ],
    )
