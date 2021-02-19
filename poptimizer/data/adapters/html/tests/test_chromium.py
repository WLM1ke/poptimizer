"""Тесты для headless браузера."""
import pytest
from pyppeteer.page import Page

from poptimizer.data.adapters.html import chromium


@pytest.fixture(scope="module", name="browser")
def create_browser():
    """Создает браузер для тестирования."""
    return chromium.Browser()


def test_browse_close_not_started(browser):
    """Попытка закрыть не запущенный браузер не вызывает ошибку."""
    assert browser._browser is None
    browser._close()


@pytest.mark.asyncio
async def test_browser_get_new_page(browser):
    """Браузер выдает разные страницы."""
    async with browser.get_new_page() as page:
        assert isinstance(page, Page)

        async with browser.get_new_page() as page2:
            assert page is not page2


def test_browse_closed(browser):
    """Отработка закрытия браузера."""
    assert browser._browser.process.returncode is None

    browser._close()

    assert browser._browser.process.returncode is not None
