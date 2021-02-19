"""Тесты для загрузки с https://finrange.com/."""
import pandas as pd
import pytest
from pyppeteer import errors

from poptimizer.data.adapters.gateways import finrange
from poptimizer.data.adapters.html import description
from poptimizer.shared import col

TICKER_CASES = (
    ("AKRN", "https://finrange.com/company/AKRN/dividends"),
    ("T-RM", "https://finrange.com/company/T/dividends"),
)


@pytest.mark.parametrize("ticker, url", TICKER_CASES)
def test_prepare_url(ticker, url):
    """У иностранных тикеров обрезается окончание."""
    assert finrange._prepare_url(ticker) == url


@pytest.mark.asyncio
async def test_load_ticker_page(mocker):
    """Загружает страницу и дожидается появления таблицы."""
    fake_browser = mocker.AsyncMock()
    fake_page = fake_browser.get_new_page.return_value

    html = await finrange._get_page_html("some_url", fake_browser)

    fake_browser.get_new_page.assert_called_once_with()
    fake_page.goto.assert_called_once_with("some_url")
    fake_page.waitForXPath.assert_called_once_with(finrange.TABLE_XPATH)

    assert html is fake_page.content.return_value


@pytest.mark.asyncio
async def test_load_ticker_page_with_error(mocker):
    """Если таблицы не удалось дождаться, то возвращается, что есть."""
    fake_browser = mocker.AsyncMock()
    fake_page = fake_browser.get_new_page.return_value
    fake_page.waitForXPath.side_effect = errors.TimeoutError

    html = await finrange._get_page_html("some_url", fake_browser)

    fake_browser.get_new_page.assert_called_once_with()
    fake_page.goto.assert_called_once_with("some_url")
    fake_page.waitForXPath.assert_called_once_with(finrange.TABLE_XPATH)

    assert html is fake_page.content.return_value


@pytest.mark.asyncio
async def test_gateway(mocker):
    """Осуществляется вызов необходимых функций."""
    fake_get_page_html = mocker.patch.object(finrange, "_get_page_html")
    fake_get_df_from_html = mocker.patch.object(finrange.parser, "get_df_from_html")
    fake_reformat_df = mocker.patch.object(finrange.description, "reformat_df_with_cur")

    gw = finrange.FinRangeGateway()
    df = await gw.__call__("AKRN")

    fake_get_page_html.assert_called_once_with(finrange._prepare_url("AKRN"))
    fake_get_df_from_html.assert_called_once_with(
        fake_get_page_html.return_value,
        finrange.TABLE_NUM,
        finrange._get_col_desc("AKRN"),
    )
    fake_reformat_df.assert_called_once_with(fake_get_df_from_html.return_value, "AKRN")

    assert df is fake_reformat_df.return_value


@pytest.mark.asyncio
async def test_gateway_error(mocker):
    """Осуществляется вызов необходимых функций."""
    mocker.patch.object(finrange, "_get_page_html")
    mocker.patch.object(finrange.parser, "get_df_from_html", side_effect=description.ParserError)

    gw = finrange.FinRangeGateway()
    df = await gw.__call__("GAZP")

    assert df is None
