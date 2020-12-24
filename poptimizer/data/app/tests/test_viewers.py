"""Тесты для просмотра данных из таблиц."""
import pandas as pd
import pytest

from poptimizer.data.app import viewers


@pytest.mark.asyncio
async def test_query_no_df(mocker):
    """Тестирование ошибки при загрузке отсутствующей таблицы."""
    fake_mapper = mocker.AsyncMock()
    fake_mapper.get_doc.return_value = {}
    viewer = viewers.Viewer(fake_mapper)

    with pytest.raises(viewers.NoDFError):
        await viewer._query("", "")


@pytest.mark.asyncio
async def test_query(mocker):
    """Тестирование загрузки таблицы."""
    fake_mapper = mocker.AsyncMock()
    df_data = {"index": [5], "columns": [6], "data": [7]}
    fake_mapper.get_doc.return_value = {"data": df_data}
    viewer = viewers.Viewer(fake_mapper)

    df = await viewer._query("", "")

    pd.testing.assert_frame_equal(df, pd.DataFrame(**df_data))


def test_get_df(mocker):
    """Для получения DataFrame осуществляется вызов запроса с правильными параметрами."""
    fake_query = mocker.AsyncMock()
    viewer = viewers.Viewer(mocker.AsyncMock())
    viewer._query = fake_query

    assert viewer.get_df("a", "b") is fake_query.return_value
    fake_query.assert_called_once_with("a", "b")


def test_get_dfs(mocker):
    """Для получения нескольких DataFrame осуществляется вызов запроса с правильными параметрами."""
    fake_query = mocker.AsyncMock()
    viewer = viewers.Viewer(mocker.AsyncMock())
    viewer._query = fake_query

    dfs = viewer.get_dfs("a", ("b", "c"))
    assert isinstance(dfs, list)
    assert len(dfs) == 2
    fake_query.assert_has_calls(
        [
            mocker.call("a", "b"),
            mocker.call("a", "c"),
        ],
    )
