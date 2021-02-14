"""Тесты для загрузки данных с NASDAQ."""
import pandas as pd
import pytest
from pyppeteer import errors

from poptimizer.data.adapters.gateways import nasdaq
from poptimizer.data.adapters.html import description
from poptimizer.shared import col


@pytest.mark.asyncio
async def test_load_ticker_page(mocker):
    """Последовательность загрузки страницы, которое завершилось полностью."""
    fake_browser = mocker.AsyncMock()
    fake_page = fake_browser.get_new_page.return_value

    html = await nasdaq._load_ticker_page("qqq", fake_browser)

    fake_browser.get_new_page.assert_called_once_with()
    fake_page.goto.assert_called_once_with("qqq", options={"timeout": nasdaq.PARTIAL_LOAD_TIMEOUT})

    assert html is fake_page.content.return_value


@pytest.mark.asyncio
async def test_load_ticker_page_wait_only_table(mocker):
    """Последовательность загрузки с ожиданием только таблицы."""
    fake_browser = mocker.AsyncMock()
    fake_page = fake_browser.get_new_page.return_value
    fake_page.goto.side_effect = errors.TimeoutError

    html = await nasdaq._load_ticker_page("qqq", fake_browser)

    fake_browser.get_new_page.assert_called_once_with()
    fake_page.goto.assert_called_once_with("qqq", options={"timeout": nasdaq.PARTIAL_LOAD_TIMEOUT})
    fake_page.waitForXPath.assert_called_once_with(nasdaq.TABLE_XPATH)

    assert html is fake_page.content.return_value


DF = pd.DataFrame(
    [[4.0], [1.0], [2.0], [None]],
    index=["2020-01-20", "2014-11-25", "2014-11-25", None],
    columns=["BELU"],
)
DF_REZ = pd.DataFrame(
    [[3.0, col.USD], [4.0, col.USD]],
    index=["2014-11-25", "2020-01-20"],
    columns=["BELU", col.CURRENCY],
)


@pytest.mark.asyncio
async def test_nasdaq_gateway(mocker):
    """Форматирование результатов с обычной загрузкой."""
    mocker.patch.object(nasdaq, "_load_ticker_page")
    mocker.patch.object(nasdaq.parser, "get_df_from_html", return_value=DF)

    gateway = nasdaq.NASDAQGateway()
    pd.testing.assert_frame_equal(await gateway.__call__("BELU"), DF_REZ)


@pytest.mark.asyncio
async def test_nasdaq_gateway_error(mocker):
    """Обработка сработавшей загрузки с ошибкой."""
    mocker.patch.object(nasdaq, "_load_ticker_page")
    mocker.patch.object(nasdaq.parser, "get_df_from_html", side_effect=description.ParserError)

    gateway = nasdaq.NASDAQGateway()
    pd.testing.assert_frame_equal(
        await gateway.__call__("BELU"),
        pd.DataFrame(columns=["BELU", col.CURRENCY]),
    )
