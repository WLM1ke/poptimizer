"""Предварительная версия интеграции с Go."""
import warnings

import aiohttp
import asyncio
import pandas as pd
from bson import json_util
from pandas import testing

from poptimizer.data import ports
from poptimizer.data.app import bootstrap
from poptimizer.portfolio import portfolio
from poptimizer.shared import connections

VIEWER = bootstrap.VIEWER


async def _rest_reader(group: str, name: str, session: aiohttp.ClientSession = connections.HTTP_SESSION):
    async with session.get(f"http://localhost:10000/api/{group}/{name}") as respond:
        respond.raise_for_status()
        json = await respond.text()

        json = json_util.loads(json)

        return pd.DataFrame(json["data"])


def rest_reader(group: str, name: str) -> pd.DataFrame:
    loop = asyncio.get_event_loop()

    return loop.run_until_complete(_rest_reader(group, name))


def securities():
    local = VIEWER.get_df(ports.SECURITIES, ports.SECURITIES)["LOT_SIZE"]
    new = rest_reader(ports.SECURITIES, ports.SECURITIES).set_index("ticker")["lot"]

    testing.assert_series_equal(local, new, check_names=False)


def cpi():
    local = VIEWER.get_df(ports.CPI, ports.CPI)
    new = rest_reader("cpi", "cpi").set_index("date")
    new.columns = local.columns

    testing.assert_frame_equal(local, new, check_names=False)


def usd():
    local = VIEWER.get_df(ports.USD, ports.USD)
    new = rest_reader(ports.USD, ports.USD).set_index("date")
    new.columns = local.columns

    testing.assert_frame_equal(local, new, check_names=False)


def indexes():
    ind = ["MCFTRR", "MEOGTRR", "IMOEX", "RVI"]

    for i in ind:
        local = VIEWER.get_df(ports.INDEX, i)
        new = rest_reader(ports.INDEX, i).set_index("date")[["close"]]
        new.columns = local.columns

        testing.assert_frame_equal(local, new, check_names=False)


def quotes(ticker: str):
    local = VIEWER.get_df(ports.QUOTES, ticker).loc["2015-01-01":]
    new = rest_reader(ports.QUOTES, ticker).set_index("date").loc["2015-01-01":]
    new.columns = local.columns

    if len(local) != len(new):
        local = local.loc[new.index[0] :]

    try:
        testing.assert_frame_equal(local, new, check_names=False, check_dtype=False)
    except:
        diff = ((local - new).abs() / local).values.mean()
        if diff > 0.015:
            print(ticker, f"{diff:.2%}")


def dividends(ticker: str):
    local = VIEWER.get_df(ports.DIVIDENDS, ticker).loc["2015-01-01":]

    try:
        new = rest_reader(ports.DIVIDENDS, ticker).set_index("date").loc["2015-01-01":]
        new.columns = local.columns
    except:
        if local.empty:
            return

        print("div", ticker)

        return

    try:
        testing.assert_frame_equal(local, new, check_names=False, check_dtype=False)
    except:
        print("div", ticker)


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        securities()
        cpi()
        usd()
        indexes()

        for ticker in portfolio.load_tickers():
            quotes(ticker)
            dividends(ticker)
