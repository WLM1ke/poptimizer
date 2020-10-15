"""Тесты общих ресурсов для загрузки и сохранения данных."""
import signal
import time

import aiohttp
import psutil
from motor import motor_asyncio

from poptimizer.data.config import resources


def test_find_running_mongo_db():
    """Находит работающую MongoDB."""
    process = resources._find_running_mongo_db()
    assert isinstance(process, psutil.Process)
    assert process.name() == "mongod"


def test_start_mongo_server():
    """Если MongoDB не запущена, то она запускается."""
    process = resources._find_running_mongo_db()
    assert process is not None
    process.send_signal(signal.SIGTERM)
    process.wait()
    assert not process.is_running()

    new_process = resources.start_mongo_server()
    time.sleep(1)
    assert new_process.name() == "mongod"
    assert new_process.pid != process.pid
    assert new_process.is_running()


def test_no_start_mongo_server():
    """Если есть работающая MongoDB, то новая не запускается."""
    process_running = resources._find_running_mongo_db()
    assert process_running is not None
    assert process_running.is_running()

    process = resources.start_mongo_server()
    assert process.pid == process_running.pid
    assert process.is_running()


def test_get_aiohttp_session():
    """Проверка, что http-сессия является асинхронной."""
    assert isinstance(resources.get_aiohttp_session(), aiohttp.ClientSession)


def test_get_mongo_client():
    """Проверка, что клиент MongoDB является асинхронным."""
    assert isinstance(resources.get_mongo_client(), motor_asyncio.AsyncIOMotorClient)


def test_clean_up(mocker):
    """Проверка закрытия http-сессии."""
    fake_session = mocker.patch.object(resources, "AIOHTTP_SESSION", new=mocker.AsyncMock())

    resources._clean_up()

    fake_session.close.assert_called_once()
