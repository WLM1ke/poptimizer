import asyncio

import pandas as pd
import pyppeteer
import pytest

from poptimizer.config import POptimizerError
from poptimizer.store import conomy
from poptimizer.store.mongo import MONGO_CLIENT


@pytest.mark.asyncio
async def test_load_ticker_page():
    browser = await pyppeteer.launch()
    try:
        page = await browser.newPage()
        await conomy.load_ticker_page(page, "FEES")
        await page.waitForXPath(conomy.DIVIDENDS_MENU)
        assert page.url == "https://www.conomy.ru/emitent/fsk-ees"
    finally:
        await browser.close()


@pytest.mark.asyncio
async def test_load_dividends_table():
    browser = await pyppeteer.launch()
    try:
        page = await browser.newPage()
        await page.goto("https://www.conomy.ru/emitent/lenenergo")
        await conomy.load_dividends_table(page)
        assert page.url == "https://www.conomy.ru/emitent/lenenergo/lsng-div"
    finally:
        await browser.close()


@pytest.mark.asyncio
async def test_get_html():
    html = await conomy.get_html("AKRN")
    assert "размер выплачиваемых ОАО «Акрон» дивидендов должен" in html


def test_is_common():
    assert conomy.is_common("CHMF")
    assert not conomy.is_common("SNGSP")
    with pytest.raises(POptimizerError) as error:
        conomy.is_common("TANGO")
    assert str(error.value) == "Некорректный тикер TANGO"


@pytest.fixture(name="manager")
def manager_in_clean_test_db():
    MONGO_CLIENT.drop_database("test")
    yield conomy.Conomy(db="test")
    MONGO_CLIENT.drop_database("test")


def test_conomy_common(manager):
    df = manager["SBER"]
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["SBER"]
    df = df["SBER"]
    assert df.size >= 9
    assert df.index[0] == pd.Timestamp("2010-04-16")
    assert df["2011-04-15"] == 0.92


def test_conomy_preferred(manager):
    df = manager["SBERP"]
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["SBERP"]
    df = df["SBERP"]
    assert isinstance(df, pd.Series)
    assert df.size >= 9
    assert df.index[0] == pd.Timestamp("2010-04-16")
    assert df["2012-04-12"] == 2.59


class FakeRun:
    def __init__(self, item):
        self._first = True
        self._value = asyncio.run(conomy.get_html(item))

    def __call__(self, *args, **kwargs):
        if self._first:
            self._first = False
            raise asyncio.TimeoutError
        return self._value


def test_conomy_reload(manager, monkeypatch):
    monkeypatch.setattr(conomy.asyncio, "run", FakeRun("SBERP"))
    df = manager["SBERP"]
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["SBERP"]
    df = df["SBERP"]
    assert isinstance(df, pd.Series)
    assert df.size >= 9
    assert df.index[0] == pd.Timestamp("2010-04-16")
    assert df["2012-04-12"] == 2.59
