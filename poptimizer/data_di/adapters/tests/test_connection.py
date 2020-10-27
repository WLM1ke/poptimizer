"""Тесты для создания http-соединения."""
import aiohttp

from poptimizer.data_di.adapters import connection


def test_session_factory():
    """Проверка, что http-сессия является асинхронной."""
    assert isinstance(connection.session_factory(10), aiohttp.ClientSession)


def test_clean_up(mocker):
    """Проверка закрытия http-сессии."""
    fake_session = mocker.AsyncMock()

    connection._clean_up(fake_session)

    fake_session.close.assert_called_once()
