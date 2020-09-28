"""Тесты для загрузки данных с https://www.smart-lab.ru."""
import pandas as pd
import pytest

from poptimizer.data.adapters.loaders import smart_lab
from poptimizer.data.ports import outer

NAMES_CASES = (
    outer.TableName(outer.SMART_LAB, "test"),
    outer.TableName(outer.QUOTES, outer.SMART_LAB),
)


@pytest.mark.parametrize("table_name", NAMES_CASES)
@pytest.mark.asyncio
async def test_loader_raise_on_wrong_name(table_name):
    """Не верное название таблицы."""
    with pytest.raises(outer.DataError, match="Некорректное имя таблицы для обновления"):
        loader = smart_lab.SmartLabLoader()
        await loader.get(table_name)


DF = pd.DataFrame(
    [[4.0], [1.0], [2.0], [None]],
    index=["2020-01-20", "2014-11-25", "2014-11-25", smart_lab.FOOTER],
)
DF_CASES = ((DF, DF.dropna()), (DF.dropna(), None))


@pytest.mark.parametrize("df_patch, df_res", DF_CASES)
@pytest.mark.asyncio
async def test_conomy_loader(mocker, df_patch, df_res):
    """Проверка нижних ячеек и отбрасывание предварительных данных."""
    mocker.patch.object(smart_lab.parser, "get_df_from_url", return_value=df_patch)
    loader = smart_lab.SmartLabLoader()
    table_name = outer.TableName(outer.SMART_LAB, outer.SMART_LAB)

    if df_res is None:
        with pytest.raises(outer.DataError, match="Некорректная html-таблица"):
            await loader.get(table_name)
    else:
        pd.testing.assert_frame_equal(await loader.get(table_name), df_res)
