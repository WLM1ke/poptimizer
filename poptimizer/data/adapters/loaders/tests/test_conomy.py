"""Тесты для загрузки с https://www.conomy.ru/."""
import pandas as pd
import pytest

from poptimizer.data.adapters.loaders import conomy
from poptimizer.data.ports import outer


@pytest.mark.asyncio
async def test_get_browser_closed(mocker):
    """Браузер закрывается после использования."""
    fake_launch = mocker.patch.object(conomy.pyppeteer, "launch")
    async with conomy._get_browser() as browser:
        assert browser is fake_launch.return_value

    browser.close.assert_called_once_with()  # noqa: WPS441


@pytest.mark.asyncio
async def test_load_ticker_page(mocker):
    """Переход на страницу с тикером."""
    fake_page = mocker.AsyncMock()
    fake_element = mocker.AsyncMock()
    fake_page.xpath.return_value = [fake_element]

    await conomy._load_ticker_page(fake_page, "TICKER")

    fake_page.goto.assert_called_once_with(conomy.SEARCH_URL)
    fake_page.xpath.assert_called_once_with(conomy.SEARCH_FIELD)
    fake_element.type.assert_called_once_with("TICKER")


@pytest.mark.asyncio
async def test_load_dividends_table(mocker):
    """Загрузка таблицы с тикером."""
    fake_page = mocker.AsyncMock()
    fake_element = mocker.AsyncMock()
    fake_page.xpath.return_value = [fake_element]

    await conomy._load_dividends_table(fake_page)

    fake_page.xpath.assert_called_once_with(conomy.DIVIDENDS_MENU)
    fake_element.click.assert_called_once_with()


@pytest.mark.asyncio
async def test_get_html(mocker):
    """Последовательный переход и загрузка html с дивидендами."""
    fake_get_browser = mocker.patch.object(conomy, "_get_browser")
    ctx_mng = fake_get_browser.return_value.__aenter__.return_value  # noqa: WPS609
    fake_page = ctx_mng.newPage.return_value
    fake_load_ticker_page = mocker.patch.object(conomy, "_load_ticker_page")
    mocker.patch.object(conomy, "_load_dividends_table")

    html = await conomy._get_html("UNAC")

    fake_get_browser.assert_called_once_with()
    fake_load_ticker_page.assert_called_once_with(fake_page, "UNAC")
    assert html is fake_page.content.return_value


TICKER_CASES = (
    ("GAZP", True),
    ("SNGSP", False),
    ("WRONG", None),
    ("AAPL-RM", None),
)


@pytest.mark.parametrize("ticker, answer", TICKER_CASES)
def test_is_common(ticker, answer):
    """Проверка, что тикер соответствует обыкновенной акции."""
    if answer is None:
        with pytest.raises(outer.DataError, match="Некорректный тикер"):
            conomy._is_common(ticker)
    else:
        assert conomy._is_common(ticker) is answer


DESC_CASES = (
    ("CHMF", 7),
    ("SNGSP", 8),
)


@pytest.mark.parametrize("ticker, answer", DESC_CASES)
def test_get_col_desc(ticker, answer):
    """Правильное составление описания в зависимости от типа акции."""
    date, div = conomy._get_col_desc(ticker)
    assert date.num == 5
    assert div.num == answer


@pytest.mark.asyncio
async def test_conomy_loader_wrong_name():
    """Исключение при неверном наименование таблицы."""
    loader = conomy.ConomyLoader()
    table_name = outer.TableName(outer.SECURITIES, "DSKY")
    with pytest.raises(outer.DataError, match="Некорректное имя таблицы для обновления"):
        await loader.get(table_name)


DF = pd.DataFrame(
    [[4.0], [1.0], [2.0], [None]],
    index=["2020-01-20", "2014-11-25", "2014-11-25", None],
    columns=["BELU"],
)
DF_REZ = pd.DataFrame(
    [[3.0], [4.0]],
    index=["2014-11-25", "2020-01-20"],
    columns=["BELU"],
)


@pytest.mark.asyncio
async def test_conomy_loader(mocker):
    """Группировка и сортировка полученных данных."""
    mocker.patch.object(conomy, "_get_html")
    mocker.patch.object(conomy, "_get_col_desc")
    mocker.patch.object(conomy.parser, "get_df_from_html", return_value=DF)

    loader = conomy.ConomyLoader()
    table_name = outer.TableName(outer.CONOMY, "BELU")
    pd.testing.assert_frame_equal(await loader.get(table_name), DF_REZ)
