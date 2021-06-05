"""Тесты загрузки данных о максимальных ставках депозитов с сайта ЦБР."""
from datetime import datetime

import pandas as pd
import pytest

from poptimizer.data.adapters.gateways import cbr
from poptimizer.data.adapters.html import parser
from poptimizer.shared import col


def test_date_parser():
    """Проверка обработки разных декад в датах."""
    assert cbr.date_parser("III.05.2021") == datetime(2021, 5, 21)
    assert cbr.date_parser("II.04.2021") == datetime(2021, 4, 11)
    assert cbr.date_parser("I.03.2021") == datetime(2021, 3, 1)
    assert cbr.date_parser("IV.03.2021") is None


DF = pd.DataFrame(
    [[4.1], [3.9]],
    index=["2020-01-20", "2014-11-25"],
    columns=[col.RF],
)
DF_REZ = pd.DataFrame(
    [[0.039], [0.041]],
    index=["2014-11-25", "2020-01-20"],
    columns=[col.RF],
)


@pytest.mark.asyncio
async def test_loader(mocker):
    """Сортировка полученных данных и перевод в проценты."""
    mocker.patch.object(parser, "get_df_from_url", return_value=DF)

    loader = cbr.RFGateway()
    pd.testing.assert_frame_equal(await loader(), DF_REZ)
