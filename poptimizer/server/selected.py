"""Ручки для редактирования выбранных тикеров."""
from __future__ import annotations

from typing import ClassVar

from aiohttp import web

from poptimizer.data.edit import selected


class SelectedView(web.View):
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
