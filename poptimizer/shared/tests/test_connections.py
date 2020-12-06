"""Тесты для общих соединений http и MongoDB."""
import signal
import time

import aiohttp
import psutil

from poptimizer.shared import connections


def test_find_running_mongo_db():
    """Находит работающую MongoDB."""
    process = connections._find_running_mongo_db()
    assert isinstance(process, psutil.Process)
    assert process.name() == "mongod"


def test_start_mongo_server():
    """Если MongoDB не запущена, то она запускается."""
    process = connections._find_running_mongo_db()
    assert process is not None
    process.send_signal(signal.SIGTERM)
    process.wait()
    assert not process.is_running()

    new_process = connections.start_mongo_server()

    time.sleep(1)
    assert new_process.name() == "mongod"
    assert new_process.pid != process.pid
    assert new_process.is_running()


def test_no_start_mongo_server():
    """Если есть работающая MongoDB, то новая не запускается."""
    process_running = connections._find_running_mongo_db()
    assert process_running is not None
    assert process_running.is_running()

    process = connections.start_mongo_server()
    assert process.pid == process_running.pid
    assert process.is_running()


def test_session_factory():
    """Проверка, что http-сессия является асинхронной."""
    assert isinstance(connections.http_session_factory(10), aiohttp.ClientSession)


def test_clean_up(mocker):
    """Проверка закрытия http-сессии."""
    fake_session = mocker.AsyncMock()

    connections._clean_up(fake_session)

    fake_session.close.assert_called_once()
