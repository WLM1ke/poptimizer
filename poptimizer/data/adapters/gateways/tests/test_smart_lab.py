"""Тесты для загрузки данных с https://www.smart-lab.ru."""
import pandas as pd
import pytest

from poptimizer.data.adapters.gateways import smart_lab
from poptimizer.data.adapters.html import parser

DF = pd.DataFrame(
    [[4.0], [1.0], [None]],
    index=["2020-01-20", "2014-11-25", "2014-11-25"],
)
DF_CASES = ((DF, DF.dropna()),)


@pytest.mark.parametrize("df_patch, df_res", DF_CASES)
@pytest.mark.asyncio
async def test_conomy_gateway(mocker, df_patch, df_res):
    """Проверка нижних ячеек и отбрасывание предварительных данных."""
    mocker.patch.object(parser, "get_df_from_url", return_value=df_patch)
    loader = smart_lab.SmartLabGateway()
    pd.testing.assert_frame_equal(await loader.__call__(), df_res)
