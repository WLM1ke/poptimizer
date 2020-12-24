"""Тесты для загрузки данных с https://www.smart-lab.ru."""
import pandas as pd
import pytest

from poptimizer.data.adapters.gateways import smart_lab
from poptimizer.data.adapters.html import description

DF = pd.DataFrame(
    [[4.0], [1.0], [2.0], [None]],
    index=["2020-01-20", "2014-11-25", "2014-11-25", smart_lab.FOOTER],
)
DF_CASES = ((DF, DF.dropna()), (DF.dropna(), None))


@pytest.mark.parametrize("df_patch, df_res", DF_CASES)
@pytest.mark.asyncio
async def test_conomy_gateway(mocker, df_patch, df_res):
    """Проверка нижних ячеек и отбрасывание предварительных данных."""
    mocker.patch.object(poptimizer.data.adapters.html.parser, "get_df_from_url", return_value=df_patch)
    loader = smart_lab.SmartLabGateway()

    if df_res is None:
        with pytest.raises(description.ParserError, match="Некорректная html-таблица"):
            await loader.get()
    else:
        pd.testing.assert_frame_equal(await loader.get(), df_res)
