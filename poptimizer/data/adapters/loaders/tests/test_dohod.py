"""Тесты для загрузки данных с https://dohod.ru."""
import pandas as pd
import pytest

from poptimizer.data.adapters.loaders import dohod
from poptimizer.data.ports import outer


@pytest.mark.asyncio
async def test_loader_raise_on_wrong_name():
    """Не верное название таблицы."""
    table_name = outer.TableName(outer.CPI, "AKRN")

    with pytest.raises(outer.DataError, match="Некорректное имя таблицы для обновления"):
        loader = dohod.DohodLoader()
        await loader.get(table_name)


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
    mocker.patch.object(dohod.parser, "get_df_from_url", return_value=DF)

    loader = dohod.DohodLoader()
    table_name = outer.TableName(outer.DOHOD, "BELU")
    pd.testing.assert_frame_equal(await loader.get(table_name), DF_REZ)


@pytest.mark.asyncio
async def test_loader_web_error(mocker):
    """Регрессионный тест при ошибке загрузки данных из интернета."""
    mocker.patch.object(dohod.parser, "get_df_from_url", side_effect=outer.DataError())

    loader = dohod.DohodLoader()
    table_name = outer.TableName(outer.DOHOD, "BELU")
    df = await loader.get(table_name)
    pd.testing.assert_frame_equal(df, pd.DataFrame(columns=["BELU"]))
