"""Тесты для загрузки котировок."""
from datetime import date, datetime

import pandas as pd
import pytest

from poptimizer.data import ports
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base, quotes
from poptimizer.shared import col


@pytest.fixture(scope="function", name="table")
def create_table():
    """Создает пустую таблицу для тестов."""
    id_ = base.create_id(ports.QUOTES, "TICKER")
    return quotes.Quotes(id_)


def test_update_cond(table):
    """Обновление происходит всегда при поступлении события."""
    assert table._update_cond(object())


COLUMNS = (col.CLOSE, col.TURNOVER)
PREPARE_CASES = (
    (
        None,
        pd.DataFrame(
            [[1, 1], [2, 4], [3, 3]],
            index=pd.Index([2, 1, 1], name=col.DATE),
            columns=COLUMNS,
        ),
        pd.DataFrame(
            [[2, 4], [1, 1]],
            index=pd.Index([1, 2], name=col.DATE),
            columns=COLUMNS,
        ),
    ),
    (
        pd.DataFrame(
            [[2, 4], [3, 3]],
            index=pd.Index([2, 1], name=col.DATE),
            columns=COLUMNS,
        ),
        pd.DataFrame(
            columns=COLUMNS,
        ),
        pd.DataFrame(
            [[2, 4], [3, 3]],
            index=pd.Index([2, 1], name=col.DATE),
            columns=COLUMNS,
        ),
    ),
    (
        pd.DataFrame(
            [[2, 4], [3, 3]],
            index=pd.Index([2, 1], name=col.DATE),
            columns=COLUMNS,
        ),
        pd.DataFrame(
            [[1, 1], [1, 4]],
            index=pd.Index([3, 5], name=col.DATE),
            columns=COLUMNS,
        ),
        pd.DataFrame(
            [[2, 4], [1, 1], [1, 4]],
            index=pd.Index([2, 3, 5], name=col.DATE),
            columns=COLUMNS,
        ),
    ),
)


@pytest.mark.asyncio
@pytest.mark.parametrize("df, df_new, df_out", PREPARE_CASES)
async def test_prepare_df(table, mocker, df, df_new, df_out):
    """Три варианта - первая загрузка, загрузка пустого и не пустого обновления."""
    table._df = df
    table._load_df = mocker.AsyncMock(return_value=df_new)

    pd.testing.assert_frame_equal(df_out, await table._prepare_df(mocker.sentinel))
    table._load_df.assert_called_once_with(mocker.sentinel)


@pytest.mark.asyncio
async def test_load_first(table, mocker):
    """Загрузка данных в первый раз."""
    fake_aliases = mocker.AsyncMock()
    fake_aliases.return_value = ["ALIAS"]
    table._aliases = fake_aliases

    table._quotes = mocker.AsyncMock()

    mocker.patch.object(quotes.pd, "concat")

    event = events.TickerTraded(
        "TICKER",
        "ISIN",
        "M1",
        date(2020, 12, 16),
        mocker.Mock(),
    )

    assert await table._load_df(event) is quotes.pd.concat.return_value
    fake_aliases.assert_called_once_with("ISIN")
    table._quotes.assert_called_once_with("ALIAS", "M1", None, "2020-12-16")


@pytest.mark.asyncio
async def test_load_after_empty(table, mocker):
    """Загрузка данных для пустых старых."""
    table._df = pd.DataFrame()
    table._aliases = mocker.AsyncMock()
    table._quotes = mocker.AsyncMock()

    mocker.patch.object(quotes.pd, "concat")

    event = events.TickerTraded(
        "TICKER",
        "ISIN",
        "M1",
        date(2020, 12, 16),
        mocker.Mock(),
    )

    assert await table._load_df(event) is quotes.pd.concat.return_value
    assert table._aliases.call_count == 0
    table._quotes.assert_called_once_with("TICKER", "M1", None, "2020-12-16")


@pytest.mark.asyncio
async def test_load_after_not_empty(table, mocker):
    """Загрузка данных для пустых старых."""
    table._df = pd.DataFrame(
        [1, 2],
        index=[datetime(2020, 12, 1), datetime(2020, 12, 11)],
    )
    table._aliases = mocker.AsyncMock()
    table._quotes = mocker.AsyncMock()

    mocker.patch.object(quotes.pd, "concat")

    event = events.TickerTraded(
        "TICKER",
        "ISIN",
        "M1",
        date(2020, 12, 16),
        mocker.Mock(),
    )

    assert await table._load_df(event) is quotes.pd.concat.return_value
    assert table._aliases.call_count == 0
    table._quotes.assert_called_once_with("TICKER", "M1", "2020-12-11", "2020-12-16")


def test_validate_new_df(table, mocker):
    """Осуществляется проверка на уникальность и согласованность данных."""
    mocker.patch.object(base, "check_unique_increasing_index")
    mocker.patch.object(base, "check_dfs_mismatch")

    table._validate_new_df(mocker.sentinel)

    base.check_unique_increasing_index.assert_called_once_with(mocker.sentinel)
    base.check_dfs_mismatch.assert_called_once_with(table.id_, None, mocker.sentinel)


def test_new_events(table):
    """Не возвращает новых событий."""
    new_events = table._new_events(object())

    assert isinstance(new_events, list)
    assert not new_events
