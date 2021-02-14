"""Headless браузер на базе Chromium для доступа к динамическим сайтам."""
import asyncio
import atexit
import types
from typing import Final, Optional

from pyppeteer import browser, launch
from pyppeteer.page import Page

# Минимальный заголовок поля в заголовке запроса, чтобы сайты  не игнорировали браузер
HEADER: Final = types.MappingProxyType(
    {
        "accept-language": "",
        "Connection": "keep-alive",
        "User-Agent": "",
    },
)


class Browser:
    """Headless браузер, который запускается по необходимости."""

    def __init__(self) -> None:
        """Создает переменную для хранения браузера."""
        self._browser: Optional[browser.Browser] = None
        self._lock = asyncio.Lock()

    async def get_new_page(self) -> Page:
        """Новая страница headless браузера.

        При необходимости загружает браузер.
        """
        async with self._lock:
            if self._browser is None:
                self._browser = await launch(autoClose=False)
                atexit.register(self._close)

        page = await self._browser.newPage()
        # В заголовке обязательно должны присутствовать определенные элементы - без них не грузятся сайты
        await page.setExtraHTTPHeaders(HEADER)
        return page

    def _close(self) -> None:
        """Закрывает браузер."""
        if self._browser is not None:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._browser.close())


BROWSER: Final = Browser()
