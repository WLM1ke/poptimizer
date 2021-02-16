"""Тесты для загрузки данных с https://закрытияреестров.рф/."""
import pandas as pd
import pytest

from poptimizer.data.adapters.gateways import close_reestry
from poptimizer.data.adapters.html import description, parser
from poptimizer.shared import col

DF = pd.DataFrame(
    [[4.0], [1.0], [2.0]],
    index=["2020-01-20", "2014-11-25", "2014-11-25"],
    columns=["TATNP"],
)
DF_REZ = pd.DataFrame(
    [[4.0, col.RUR], [1.0, col.RUR], [2.0, col.RUR]],
    index=["2020-01-20", "2014-11-25", "2014-11-25"],
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
    pd.testing.assert_frame_equal(df, pd.DataFrame(columns=["TATN", col.CURRENCY]))
