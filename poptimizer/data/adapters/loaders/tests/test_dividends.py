"""Тесты для загрузки локальных данных по дивидендам."""
import pandas as pd
import pytest

from poptimizer.data.adapters.loaders import dividends
from poptimizer.data.ports import col, outer


@pytest.mark.asyncio
async def test_loader_raise_on_wrong_name():
    """Не верное название таблицы."""
    table_name = outer.TableName(outer.CPI, "AKRN")

    with pytest.raises(outer.DataError, match="Некорректное имя таблицы для обновления"):
        loader = dividends.DividendsLoader()
        await loader.get(table_name)


@pytest.mark.asyncio
async def test_loader(mocker):
    """Форматирование загруженного DataFrame."""
    fake_client = mocker.patch.object(dividends.resources, "get_mongo_client")
    fake_db = fake_client.return_value.__getitem__.return_value  # noqa: WPS609
    fake_collection = fake_db.__getitem__.return_value  # noqa: WPS609
    fake_collection.aggregate.return_value = mocker.AsyncMock()
    mocker.patch.object(dividends.pd, "DataFrame", return_value=pd.DataFrame(columns=[1, 2]))

    loader = dividends.DividendsLoader()
    df = await loader.get(outer.TableName(outer.DIVIDENDS, "AKRN"))

    assert df.index.name == col.DATE
    assert df.columns == ["AKRN"]
