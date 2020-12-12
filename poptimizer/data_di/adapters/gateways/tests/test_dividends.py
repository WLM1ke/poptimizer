"""Тесты для загрузки локальных данных по дивидендам."""
import pandas as pd
import pytest

from poptimizer.data_di.adapters.gateways import dividends


@pytest.mark.asyncio
async def test_div_gateway(mocker):
    """Форматирование загруженного DataFrame."""
    fake_collection = mocker.Mock()
    fake_cursor = mocker.AsyncMock()
    fake_collection.find.return_value = fake_cursor
    fake_cursor.to_list.return_value = [
        {"date": 2, "dividends": 1},
        {"date": 2, "dividends": 2},
        {"date": 1, "dividends": 4},
    ]

    gw = dividends.DividendsGateway(fake_collection)
    df = await gw.get("AKRN")

    assert df.columns.tolist() == ["AKRN"]
    assert df.index.tolist() == [1, 2]
    assert df.values.tolist() == [[4], [3]]


@pytest.mark.asyncio
async def test_div_gateway_empty_data(mocker):
    """Регрессионный тест на пустые данные в базе."""
    fake_collection = mocker.Mock()
    fake_cursor = mocker.AsyncMock()
    fake_collection.find.return_value = fake_cursor
    fake_cursor.to_list.return_value = []

    gw = dividends.DividendsGateway(fake_collection)
    df = await gw.get("ISKJ")

    pd.testing.assert_frame_equal(df, pd.DataFrame(columns=["ISKJ"]))
