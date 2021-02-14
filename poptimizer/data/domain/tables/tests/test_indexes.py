"""Тесты для таблиц с индексами MOEX."""
from datetime import date, datetime

import pandas as pd
import pytest

from poptimizer.data import ports
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base, indexes


@pytest.fixture(scope="function", name="table")
def create_table():
    """Создает пустую таблицу для тестов."""
    id_ = base.create_id(ports.INDEX, "SOME_INDEX")
    return indexes.Indexes(id_)


def test_update_cond(table):
    """Обновление происходит всегда при поступлении события."""
    assert table._update_cond(object())


@pytest.mark.asyncio
async def test_prepare_df_for_new_table(table, mocker):
    """Если таблица без данных, то осуществляется загрузка с начала."""
    event = events.IndexCalculated("TICKER", date(2020, 12, 15))
    fake_gateway = mocker.AsyncMock()
    table._gateway = fake_gateway

    assert await table._prepare_df(event) == fake_gateway.return_value
    fake_gateway.assert_called_once_with("TICKER", None, "2020-12-15")


@pytest.mark.asyncio
async def test_prepare_df_for_update_table(table, mocker):
    """Если таблица c данных, то осуществляется инкрементальная загрузка."""
    event = events.IndexCalculated("TICKER", date(2020, 12, 15))
    fake_gateway = mocker.AsyncMock()
    fake_gateway.return_value = pd.DataFrame(
        [2, 1],
        index=[
            datetime(2020, 12, 14),
            datetime(2020, 12, 15),
        ],
    )
    table._gateway = fake_gateway
    table._df = pd.DataFrame(
        [3, 2],
        index=[
            datetime(2020, 12, 13),
            datetime(2020, 12, 14),
        ],
    )

    new_df = await table._prepare_df(event)
    pd.testing.assert_frame_equal(
        new_df,
        pd.DataFrame(
            [3, 2, 1],
            index=[
                datetime(2020, 12, 13),
                datetime(2020, 12, 14),
                datetime(2020, 12, 15),
            ],
        ),
    )
    fake_gateway.assert_called_once_with("TICKER", "2020-12-14", "2020-12-15")


def test_validate_new_df(mocker, table):
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
