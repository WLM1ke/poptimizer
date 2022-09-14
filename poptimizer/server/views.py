"""Раздача статики Frontend и ручки Backend."""
from typing import ClassVar

from aiohttp import web

from poptimizer import consts
from poptimizer.data.edit import dividends, selected


class Selected(web.View):
    """Ручки для редактирования выбранных тикеров."""

    _srv: ClassVar[selected.Service]

    @classmethod
    def register(cls, app: web.Application, srv: selected.Service) -> None:
        """Регистрирует ручки для редактирования выбранных тикеров и внедряет необходимую службу."""
        cls._srv = srv
        app.router.add_view("/tickers", cls)

    async def get(self) -> web.StreamResponse:
        """Получение данных о выбранных тикерах."""
        dto = await self._srv.get()

        return web.json_response(text=dto.json())

    async def put(self) -> None:
        """Обновление данных о выбранных тикерах."""
        dto = selected.DTO.parse_raw(await self.request.text())
        await self._srv.save(dto)

        raise web.HTTPOk


class Dividends(web.View):
    """Ручки для сверки и редактирования дивидендов."""

    _srv: ClassVar[dividends.Service]

    @classmethod
    def register(cls, app: web.Application, srv: dividends.Service) -> None:
        """Регистрирует ручки для сверки и редактирования дивидендов и внедряет необходимую службу."""
        cls._srv = srv

        app.add_routes([web.get("/dividends", cls.get_tickers)])
        app.router.add_view("/dividends/{ticker}", cls)

    @classmethod
    async def get_tickers(cls, _: web.Request) -> web.StreamResponse:
        """Возвращает список тикеров на выбор для редактирования дивидендов."""
        dto = await cls._srv.get_tickers()

        return web.json_response(text=dto.json())

    async def get(self) -> web.StreamResponse:
        """Получение данных о дивидендах."""
        ticker = self.request.match_info["ticker"]
        dto = await self._srv.get_dividends(ticker)

        return web.json_response(text=dto.json())

    async def put(self) -> None:
        """Обновление данных о дивидендах."""
        ticker = self.request.match_info["ticker"]
        dto = dividends.SaveDividendsDTO.parse_raw(await self.request.text())
        await self._srv.save_dividends(ticker, dto)

        raise web.HTTPOk


class Frontend(web.View):
    """Отображение главной страницы."""

    _static: ClassVar = consts.ROOT_PATH / "static"

    @classmethod
    def register(cls, app: web.Application) -> None:
        """Регистрирует необходимые для отображения главной страницы ресурсы."""
        app.router.add_view("/", cls)
        app.router.add_static("/", cls._static)

    async def get(self) -> web.StreamResponse:
        """Главная страничка приложения."""
        return web.FileResponse(self._static / "index.html")
