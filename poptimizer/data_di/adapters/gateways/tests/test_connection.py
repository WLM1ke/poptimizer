"""Тесты для создания http-соединения."""
import aiohttp

import poptimizer.shared.connections
from poptimizer.data_di.adapters.gateways import base


def test_session_factory():
    """Проверка, что http-сессия является асинхронной."""
    assert isinstance(poptimizer.shared.connections._session_factory(10), aiohttp.ClientSession)


def test_clean_up(mocker):
    """Проверка закрытия http-сессии."""
    fake_session = mocker.AsyncMock()

    poptimizer.shared.connections._clean_up(fake_session)

    fake_session.close.assert_called_once()
