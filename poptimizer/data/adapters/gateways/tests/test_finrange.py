"""Тесты для загрузки с https://finrange.com/."""
import pandas as pd
import pytest

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


DIV_CASES = (
    ("2 027,5  ₽", "2027.5RUR"),
    ("2,1  $", "2.1USD"),
    ("", None),
)


@pytest.mark.parametrize("div, div_parsed", DIV_CASES)
def test_div_parser(div, div_parsed):
    """У иностранных тикеров обрезается окончание."""
    assert finrange._div_parser(div) == div_parsed


def test_reformat_df():
    """Данные разносятся на два столбца."""
    div = pd.DataFrame(["2027.5RUR", "2.1USD"], columns=["SOME"])
    div_reformatted = pd.DataFrame(
        [[2027.5, "RUR"], [2.1, "USD"]],
        columns=["SOME", col.CURRENCY],
    )

    pd.testing.assert_frame_equal(finrange._reformat_df(div, "SOME"), div_reformatted)


@pytest.mark.asyncio
async def test_gateway(mocker):
    """Осуществляется вызов необходимых функций."""
    fake_get_page_html = mocker.patch.object(finrange, "_get_page_html")
    fake_get_df_from_html = mocker.patch.object(finrange.parser, "get_df_from_html")
    fake_reformat_df = mocker.patch.object(finrange, "_reformat_df")

    gw = finrange.FinRangeGateway()
    df = await gw.get("AKRN")

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
    df = await gw.get("GAZP")

    pd.testing.assert_frame_equal(df, pd.DataFrame(columns=["GAZP", col.CURRENCY]))
