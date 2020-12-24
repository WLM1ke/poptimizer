"""Тесты для таблицы с потребительской инфляцией."""
from datetime import datetime

import pandas as pd
import pytest

from poptimizer.data import ports
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base, cpi

UPDATE_CASES = (
    (
        None,
        datetime(2020, 12, 14),
        True,
    ),
    (
        pd.DataFrame(index=[datetime(2020, 10, 14)]),
        datetime(2020, 12, 14),
        True,
    ),
    (
        pd.DataFrame(index=[datetime(2020, 11, 14)]),
        datetime(2020, 12, 14),
        False,
    ),
)


@pytest.mark.parametrize("df, event_date, update", UPDATE_CASES)
def test_update_cond(df, event_date, update):
    """Индекс обновляется при отсутствии и по окончании месяца."""
    event = events.TradingDayEnded(event_date)
    id_ = base.create_id(ports.CPI)
    table = cpi.CPI(id_, df=df)

    assert table._update_cond(event) == update


@pytest.mark.asyncio
async def test_prepare_df(mocker):
    """Вызов по подготовке DataFrame переадресуется шлюзу."""
    id_ = base.create_id(ports.CPI)
    table = cpi.CPI(id_)
    fake_gateway = mocker.AsyncMock()
    table._gateway = fake_gateway

    assert await table._prepare_df("") == fake_gateway.get.return_value


def test_validate_new_df(mocker):
    """Осуществляется проверка на уникальность и согласованность данных."""
    mocker.patch.object(base, "check_unique_increasing_index")
    mocker.patch.object(base, "check_dfs_mismatch")

    id_ = base.create_id(ports.CPI)
    table = cpi.CPI(id_)

    table._validate_new_df(mocker.sentinel)

    base.check_unique_increasing_index.assert_called_once_with(mocker.sentinel)
    base.check_dfs_mismatch.assert_called_once_with(id_, None, mocker.sentinel)


def test_new_events():
    """Не возвращает новых событий."""
    id_ = base.create_id(ports.CPI)
    table = cpi.CPI(id_)

    new_events = table._new_events("")

    assert isinstance(new_events, list)
    assert not new_events
