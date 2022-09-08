"""Отображение главной страницы."""
from pathlib import Path
from typing import ClassVar

from aiohttp import web


class FrontendView(web.View):
    """Отображение главной страницы."""

    _static: ClassVar = Path(__file__).parents[2] / "static"

    @classmethod
    def register(cls, app: web.Application) -> None:
        """Регистрирует необходимые для отображения главной страницы ресурсы."""
        app.router.add_view("/", cls)
        app.router.add_static("/", cls._static)

    async def get(self) -> web.StreamResponse:
        """Главная страничка приложения."""
        return web.FileResponse(self._static / "index.html")
