"""Раздача статики Frontend и ручки Backend."""
from typing import ClassVar

from aiohttp import web

from poptimizer.core import consts
from poptimizer.data.edit import dividends
from poptimizer.portfolio.edit import accounts, portfolio, selected


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


class Accounts(web.View):
    """Ручки для редактирования состава брокерских счетов."""

    _srv: ClassVar[accounts.Service]

    @classmethod
    def register(cls, app: web.Application, srv: accounts.Service) -> None:
        """Регистрирует ручки для редактирования состава брокерских счетов и внедряет необходимую службу."""
        cls._srv = srv

        app.add_routes([web.get("/accounts", cls.get_account_names)])
        app.router.add_view("/accounts/{acc_name}", cls)

    @classmethod
    async def get_account_names(cls, _: web.Request) -> web.StreamResponse:
        """Возвращает перечень существующих брокерских счетов."""
        dto = await cls._srv.get_account_names()

        return web.json_response(text=dto.json())

    @property
    def acc_name(self) -> str:
        """Наименование счета из запроса."""
        return self.request.match_info["acc_name"]

    async def get(self) -> web.StreamResponse:
        """Получение данных о выбранных тикерах."""
        dto = await self._srv.get_account(self.acc_name)

        return web.json_response(text=dto.json())

    async def post(self) -> None:
        """Создает брокерский счет, если он не существует."""
        await self._srv.create_account(self.acc_name)

        raise web.HTTPOk

    async def put(self) -> None:
        """Обновляет данные о количестве бумаг на счете."""
        dto = accounts.AccountUpdateDTO.parse_raw(await self.request.text())

        await self._srv.update_account(self.acc_name, dto)

        raise web.HTTPOk

    async def delete(self) -> None:
        """Удаляет брокерский счет, если он пустой."""
        await self._srv.remove_account(self.acc_name)

        raise web.HTTPOk


class Portfolio(web.View):
    """Ручки для просмотра состава портфеля."""

    _srv: ClassVar[portfolio.Service]

    @classmethod
    def register(cls, app: web.Application, srv: portfolio.Service) -> None:
        """Регистрирует ручки для редактирования состава брокерских счетов и внедряет необходимую службу."""
        cls._srv = srv

        app.add_routes([web.get("/portfolio", cls.get_account_names)])
        app.router.add_view("/portfolio/{date}", cls)

    @classmethod
    async def get_account_names(cls, _: web.Request) -> web.StreamResponse:
        """Возвращает перечень существующих дат, на которые есть информация о портфеле."""
        dto = await cls._srv.get_dates()

        return web.json_response(text=dto.json())

    async def get(self) -> web.StreamResponse:
        """Выдает сводную информацию о портфеле по всем брокерским счетам."""
        date = self.request.match_info["date"]

        dto = await self._srv.get_portfolio(date)

        return web.json_response(text=dto.json())


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
