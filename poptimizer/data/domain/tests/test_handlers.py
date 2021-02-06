"""Тесты для обработчиков доменных событий."""
from datetime import date

import pandas as pd
import pytest

from poptimizer.data import ports
from poptimizer.data.domain import events, handlers
from poptimizer.data.domain.tables import base
from poptimizer.shared import domain


@pytest.mark.asyncio
async def test_load_by_id_and_handle_event(mocker):
    """Тестирование корректности загрузки таблицы и обработки события."""
    fake_repo = mocker.AsyncMock()
    fake_id = mocker.AsyncMock()
    fake_event = mocker.AsyncMock()

    rez = await handlers._load_by_id_and_handle_event(fake_repo, fake_id, fake_event)

    fake_repo.get.assert_called_once_with(fake_id)
    fake_table = fake_repo.get.return_value
    fake_table.handle_event.assert_called_once_with(fake_event)
    assert rez is fake_table.handle_event.return_value


@pytest.mark.asyncio
async def test_handle_raise_on_unknown_event(mocker):
    """При обработке неизвестного события выбрасывается исключение."""
    dispatcher = handlers.EventHandlersDispatcher()
    with pytest.raises(handlers.UnknownEventError):
        await dispatcher.handle_event(domain.AbstractEvent(), mocker.AsyncMock())


@pytest.mark.asyncio
async def test_handle_app_started(mocker):
    """Обработка события начала приложения обновляет таблицу с торговыми датами."""
    dispatcher = handlers.EventHandlersDispatcher()
    event = events.AppStarted()
    fake_repo = mocker.Mock()
    fake_loader_and_handler = mocker.patch.object(handlers, "_load_by_id_and_handle_event")

    assert await dispatcher.handle_event(event, fake_repo) is fake_loader_and_handler.return_value
    fake_loader_and_handler.assert_called_once_with(
        fake_repo,
        base.create_id(ports.TRADING_DATES),
        event,
    )


@pytest.mark.asyncio
async def test_trading_day_ended(mocker):
    """В конце торгового дня должны обновляться базовые данные.

    Создаются события для обновления индексов и осуществляется обновление трех таблиц.
    """
    dispatcher = handlers.EventHandlersDispatcher()
    event = events.TradingDayEnded(date(2020, 12, 22))
    fake_repo = mocker.Mock()
    mocker.patch.object(
        handlers,
        "_load_by_id_and_handle_event",
        side_effect=[["a"], ["b", "c"], ["usd"]],
    )

    assert await dispatcher.handle_event(event, fake_repo) == [
        events.IndexCalculated("MCFTRR", event.date),
        events.IndexCalculated("IMOEX", event.date),
        events.IndexCalculated("RVI", event.date),
        "a",
        "b",
        "c",
        "usd",
    ]


@pytest.mark.asyncio
async def test_usd_traded(mocker):
    """После загрузки курса началось обновление данных о торгуемых бумагах."""
    dispatcher = handlers.EventHandlersDispatcher()
    event = events.USDUpdated(date=date(2021, 2, 5), usd=pd.DataFrame)
    fake_repo = mocker.Mock()
    fake_loader_and_handler = mocker.patch.object(handlers, "_load_by_id_and_handle_event")

    assert await dispatcher.handle_event(event, fake_repo) is fake_loader_and_handler.return_value
    fake_loader_and_handler.assert_called_once_with(
        fake_repo,
        base.create_id(ports.SECURITIES),
        event,
    )


@pytest.mark.asyncio
async def test_ticker_traded(mocker):
    """Для торгуемого тикера должны обновляться котировки и дивиденды."""
    dispatcher = handlers.EventHandlersDispatcher()
    event = events.TickerTraded(
        "ticker",
        "ISIN",
        "M1",
        date(2020, 12, 22),
        pd.DataFrame([1]),
    )
    fake_repo = mocker.Mock()
    fake_load_by_id_and_handle_event = mocker.patch.object(
        handlers,
        "_load_by_id_and_handle_event",
        side_effect=[["aa"], ["bb", "cc"]],
    )

    assert await dispatcher.handle_event(event, fake_repo) == ["aa", "bb", "cc"]

    fake_load_by_id_and_handle_event.assert_has_calls(
        [
            mocker.call(fake_repo, base.create_id(ports.QUOTES, "ticker"), event),
            mocker.call(fake_repo, base.create_id(ports.DIVIDENDS, "ticker"), event),
        ],
    )


@pytest.mark.asyncio
async def test_index_calculated(mocker):
    """Требуется обновить таблицу с индексом."""
    dispatcher = handlers.EventHandlersDispatcher()
    event = events.IndexCalculated("IND1", date(2020, 12, 22))
    fake_repo = mocker.Mock()
    fake_loader_and_handler = mocker.patch.object(handlers, "_load_by_id_and_handle_event")

    assert await dispatcher.handle_event(event, fake_repo) is fake_loader_and_handler.return_value
    fake_loader_and_handler.assert_called_once_with(
        fake_repo,
        base.create_id(ports.INDEX, "IND1"),
        event,
    )


@pytest.mark.asyncio
async def test_div_expected(mocker):
    """Требуется обновить таблицу с внешними данными по дивидендам."""
    dispatcher = handlers.EventHandlersDispatcher()
    event = events.DivExpected("TICKER1", pd.DataFrame())
    fake_repo = mocker.Mock()
    fake_loader_and_handler = mocker.patch.object(handlers, "_load_by_id_and_handle_event")

    assert await dispatcher.handle_event(event, fake_repo) is fake_loader_and_handler.return_value
    fake_loader_and_handler.assert_called_once_with(
        fake_repo,
        base.create_id(ports.DIV_EXT, "TICKER1"),
        event,
    )


@pytest.mark.asyncio
async def test_update_div(mocker):
    """Требуется обновить таблицу с внутренними и внешними данными по дивидендам."""
    dispatcher = handlers.EventHandlersDispatcher()
    event = events.UpdateDivCommand("TICKER3")
    fake_repo = mocker.Mock()
    mocker.patch.object(handlers, "_load_by_id_and_handle_event", return_value=["event1", "event2"])

    first, *other = await dispatcher.handle_event(event, fake_repo)

    assert isinstance(first, events.DivExpected)
    assert first.ticker == "TICKER3"
    pd.testing.assert_frame_equal(first.df, pd.DataFrame(columns=["SmartLab"]))
    assert other == ["event1", "event2"]
