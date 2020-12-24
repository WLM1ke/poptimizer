"""Тесты для загрузки данных с https://dohod.ru."""
import pandas as pd
import pytest

from poptimizer.data.adapters.gateways import dohod
from poptimizer.data.adapters.html import description

DF = pd.DataFrame(
    [[4.0], [1.0], [2.0]],
    index=["2020-01-20", "2014-11-25", "2014-11-25"],
    columns=["BELU"],
)
DF_REZ = pd.DataFrame(
    [[3.0], [4.0]],
    index=["2014-11-25", "2020-01-20"],
    columns=["BELU"],
)


@pytest.mark.asyncio
async def test_loader(mocker):
    """Группировка и сортировка полученных данных."""
    mocker.patch.object(poptimizer.data.adapters.html.parser, "get_df_from_url", return_value=DF)

    loader = dohod.DohodGateway()
    pd.testing.assert_frame_equal(await loader.get("BELU"), DF_REZ)


@pytest.mark.asyncio
async def test_loader_web_error(mocker):
    """Регрессионный тест при ошибке загрузки данных из интернета."""
    mocker.patch.object(
        poptimizer.data.adapters.html.parser, "get_df_from_url", side_effect=description.ParserError()
    )

    loader = dohod.DohodGateway()
    df = await loader.get("BELU")
    pd.testing.assert_frame_equal(df, pd.DataFrame(columns=["BELU"]))
