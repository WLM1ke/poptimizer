from datetime import date
from unittest import mock
from unittest.mock import AsyncMock, Mock

import pytest

import poptimizer.domain.div.div as div_domain
import poptimizer.domain.div.raw as raw_domain
import poptimizer.domain.moex.securities as securities_domain
import poptimizer.use_cases.div.div as div_handler
from poptimizer.domain import domain
from poptimizer.use_cases import handler

_TEST_MSG_DATE = date(2023, 1, 1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "securities_data",
    [
        [],
        ["TICKER1"],
        ["TICKER1", "TICKER2"],
    ],
)
async def test_call_creates_tasks_for_each_security(securities_data):
    mock_ctx = AsyncMock()
    mock_securities_table = Mock()

    securities_list = []
    for ticker in securities_data:
        mock_security = Mock()
        mock_security.ticker = ticker
        securities_list.append(mock_security)

    mock_securities_table.df = securities_list
    mock_ctx.get.return_value = mock_securities_table

    handler_obj = div_handler.DivHandler()
    handler_obj._update_one = AsyncMock()

    msg = handler.SecuritiesUpdated(day=_TEST_MSG_DATE)

    result = await handler_obj(mock_ctx, msg)

    mock_ctx.get.assert_called_once_with(securities_domain.Securities)

    expected_call_count = len(securities_data)
    assert handler_obj._update_one.call_count == expected_call_count

    expected_calls = [mock.call(mock_ctx, _TEST_MSG_DATE, domain.UID(ticker)) for ticker in securities_data]
    handler_obj._update_one.assert_has_calls(expected_calls, any_order=True)

    assert result == handler.DivUpdated(day=_TEST_MSG_DATE)


@pytest.mark.asyncio
async def test_update_one_calls_get_for_update_with_correct_params():
    mock_ctx = AsyncMock()
    mock_div_table = Mock()
    mock_raw_table = Mock()

    mock_ctx.get_for_update.return_value = mock_div_table
    mock_ctx.get.return_value = mock_raw_table

    mock_raw_table.df = []

    handler_obj = div_handler.DivHandler()

    await handler_obj._update_one(mock_ctx, _TEST_MSG_DATE, domain.UID("ABC"))

    mock_ctx.get_for_update.assert_called_once_with(div_domain.Dividends, domain.UID("ABC"))

    mock_ctx.get.assert_called_once_with(raw_domain.DivRaw, domain.UID("ABC"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("raw_rows", "expected_rows"),
    [
        ([], []),
        (
            [raw_domain.Row(day=_TEST_MSG_DATE, dividend=10.0)],
            [div_domain.Row(day=_TEST_MSG_DATE, dividend=10.0)],
        ),
        (
            [
                raw_domain.Row(day=_TEST_MSG_DATE, dividend=10.0),
                raw_domain.Row(day=_TEST_MSG_DATE, dividend=5.0),
            ],
            [div_domain.Row(day=_TEST_MSG_DATE, dividend=15.0)],
        ),
        (
            [
                raw_domain.Row(day=_TEST_MSG_DATE, dividend=10.0),
                raw_domain.Row(day=date(2023, 1, 2), dividend=5.0),
            ],
            [
                div_domain.Row(day=_TEST_MSG_DATE, dividend=10.0),
                div_domain.Row(day=date(2023, 1, 2), dividend=5.0),
            ],
        ),
        (
            [
                raw_domain.Row(day=_TEST_MSG_DATE, dividend=1.0),
                raw_domain.Row(day=_TEST_MSG_DATE, dividend=2.0),
                raw_domain.Row(day=_TEST_MSG_DATE, dividend=3.0),
                raw_domain.Row(day=date(2023, 1, 10), dividend=10.0),
                raw_domain.Row(day=date(2023, 1, 10), dividend=15.0),
                raw_domain.Row(day=date(2023, 2, 1), dividend=100.0),
            ],
            [
                div_domain.Row(day=_TEST_MSG_DATE, dividend=6.0),
                div_domain.Row(day=date(2023, 1, 10), dividend=25.0),
                div_domain.Row(day=date(2023, 2, 1), dividend=100.0),
            ],
        ),
    ],
)
async def test_prepare_rows_via_update_one(raw_rows, expected_rows):
    mock_ctx = AsyncMock()
    mock_div_table = Mock()
    mock_raw_table = Mock()

    mock_ctx.get_for_update.return_value = mock_div_table
    mock_ctx.get.return_value = mock_raw_table

    mock_raw_table.df = raw_rows

    handler_obj = div_handler.DivHandler()
    update_day = _TEST_MSG_DATE
    ticker = domain.UID("ABC")

    await handler_obj._update_one(mock_ctx, update_day, ticker)

    mock_div_table.update.assert_called_once_with(update_day, expected_rows)
