import pandas as pd
import pyppeteer
import pytest

from poptimizer import config
from poptimizer.config import POptimizerError
from poptimizer.store import client, conomy


@pytest.fixture(autouse=True)
@pytest.mark.asyncio
async def create_client(tmpdir_factory, monkeypatch):
    temp_dir = tmpdir_factory.mktemp("conomy")
    monkeypatch.setattr(config, "DATA_PATH", temp_dir)
    async with client.Client():
        yield


@pytest.mark.asyncio
async def test_load_ticker_page():
    try:
        browser = await pyppeteer.launch()
        page = await browser.newPage()
        await conomy.load_ticker_page(page, "FEES")
        await page.waitForXPath(conomy.DIVIDENDS_MENU)
        assert page.url == "https://www.conomy.ru/emitent/fsk-ees"
    finally:
        await browser.close()


@pytest.mark.asyncio
async def test_load_dividends_table():
    try:
        browser = await pyppeteer.launch()
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


@pytest.mark.asyncio
async def test_conomy_common():
    df = await conomy.Conomy(("SBER",)).get()
    assert isinstance(df, pd.Series)
    assert df.size >= 9
    assert df.index[0] == pd.Timestamp("2010-04-16")
    assert df["2011-04-15"] == 0.92


@pytest.mark.asyncio
async def test_conomy_preferred():
    df = await conomy.Conomy(("SBERP",)).get()
    assert isinstance(df, pd.Series)
    assert df.size >= 9
    assert df.index[0] == pd.Timestamp("2010-04-16")
    assert df["2012-04-12"] == 2.59
