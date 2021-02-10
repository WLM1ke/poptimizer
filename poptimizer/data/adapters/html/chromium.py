"""Headless браузер на базе Chromium для доступа к динамическим сайтам."""
import asyncio
import atexit
from typing import Final, Optional

import pyppeteer
from pyppeteer import browser
from pyppeteer.page import Page


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
                self._browser = await pyppeteer.launch(autoClose=False)
                atexit.register(self._close)
        return self._browser.newPage()

    def _close(self) -> None:
        """Закрывает браузер."""
        if self._browser is not None:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._browser.close())


BROWSER: Final = Browser()
