"""Тесты для загрузки данных с https://закрытияреестров.рф/."""
import pandas as pd
import pytest

from poptimizer.data.adapters.gateways import close_reestry
from poptimizer.data.adapters.html import description, parser
from poptimizer.shared import col

PARSER_CASE = (
    ("1,04 USD", "1.04USD"),
    ("12,29 руб.", "12.29RUR"),
    ("11 612,20 руб.", "11612.20RUR"),
    ("0,89 $", "0.89USD"),
)


@pytest.mark.parametrize("raw, output", PARSER_CASE)
def test_parser_div(raw, output):
    """Проверка работы парсера для разных валют и длинных чисел."""
    assert close_reestry.parser_div(raw) == output


DF = pd.DataFrame(
    [["4.0USD"], ["1.0RUR"], ["2.0RUR"]],
    index=["2020-01-20", "2014-11-23", "2014-11-25"],
    columns=["TATNP"],
)
DF_REZ = pd.DataFrame(
    [
        [1.0, col.RUR],
        [2.0, col.RUR],
        [4.0, col.USD],
    ],
    index=[
        "2014-11-23",
        "2014-11-25",
        "2020-01-20",
    ],
    columns=["TATNP", col.CURRENCY],
)


@pytest.mark.asyncio
async def test_loader(mocker):
    """Добавление столбца с валютами."""
    mocker.patch.object(parser, "get_df_from_url", return_value=DF)

    loader = close_reestry.CloseGateway()
    pd.testing.assert_frame_equal(await loader("TATNP"), DF_REZ)


@pytest.mark.asyncio
async def test_loader_web_error(mocker):
    """Регрессионный тест при ошибке загрузки данных из интернета."""
    mocker.patch.object(parser, "get_df_from_url", side_effect=description.ParserError())

    loader = close_reestry.CloseGateway()
    df = await loader("TATN")

    assert df is None
