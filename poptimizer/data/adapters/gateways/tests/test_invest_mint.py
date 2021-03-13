"""Тесты для загрузки данных с https://investmint.ru/."""
from datetime import datetime

import pandas as pd
import pytest

from poptimizer.data.adapters.gateways import invest_mint
from poptimizer.data.adapters.html import description
from poptimizer.shared import col


def test_date_parser():
    """Парсер для дат."""
    assert invest_mint._date_parser("") is None
    assert invest_mint._date_parser("7 дек 2018") == datetime(2018, 12, 7)
    assert invest_mint._date_parser("28 мая 2020") == datetime(2020, 5, 28)
    assert invest_mint._date_parser("1 дек 2017") == datetime(2017, 12, 1)


DF = pd.DataFrame(
    [["4.0RUR"], ["1.0USD"], ["2.0RUR"]],
    index=["2020-01-20", "2014-11-25", "2014-11-25"],
    columns=["BELU"],
)
DF_REZ = pd.DataFrame(
    [[4.0, col.RUR], [1.0, col.USD], [2.0, col.RUR]],
    index=["2020-01-20", "2014-11-25", "2014-11-25"],
    columns=["BELU", col.CURRENCY],
)
CASES = ((DF, "<table>Цена на закрытии<\table>", DF_REZ),)


@pytest.mark.parametrize("df, html, df_rez", CASES)
@pytest.mark.asyncio
async def test_loader(mocker, df, html, df_rez):
    """Форматирование данных."""
    mocker.patch.object(invest_mint.parser, "get_html", return_value=html)
    mocker.patch.object(invest_mint.parser, "get_df_from_html", return_value=df.copy())

    gw = invest_mint.InvestMintGateway()

    pd.testing.assert_frame_equal(await gw("BELU"), df_rez)


@pytest.mark.asyncio
async def test_loader_get_html_error(mocker):
    """Регрессионный тест при ошибке загрузки данных из интернета."""
    mocker.patch.object(invest_mint.parser, "get_html", side_effect=description.ParserError())

    loader = invest_mint.InvestMintGateway()
    df = await loader("BELU")

    assert df is None


@pytest.mark.asyncio
async def test_loader_get_df_from_html_error(mocker):
    """Регрессионный тест при парсинге данных."""
    mocker.patch.object(invest_mint.parser, "get_html", return_value="")
    mocker.patch.object(invest_mint.parser, "get_df_from_html", side_effect=description.ParserError())

    loader = invest_mint.InvestMintGateway()
    df = await loader("BELU")

    assert df is None
