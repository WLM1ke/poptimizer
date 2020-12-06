"""Тесты для общих соединений http и MongoDB."""
import aiohttp

from poptimizer.shared import connections


def test_session_factory():
    """Проверка, что http-сессия является асинхронной."""
    assert isinstance(connections._session_factory(10), aiohttp.ClientSession)


def test_clean_up(mocker):
    """Проверка закрытия http-сессии."""
    fake_session = mocker.AsyncMock()

    connections._clean_up(fake_session)

    fake_session.close.assert_called_once()
