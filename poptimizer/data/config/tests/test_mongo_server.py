"""Тесты для запуска сервера MongoDB."""
import signal
import time

import psutil

from poptimizer.data.config import mongo_server


def test_find_running_mongo_db():
    """Находит работающую MongoDB."""
    process = mongo_server._find_running_mongo_db()
    assert isinstance(process, psutil.Process)
    assert process.name() == "mongod"


def test_start_mongo_server():
    """Если MongoDB не запущена, то она запускается."""
    process = mongo_server._find_running_mongo_db()
    assert process is not None
    process.send_signal(signal.SIGTERM)
    process.wait()
    assert not process.is_running()

    new_process = mongo_server.start_mongo_server()
    time.sleep(1)
    assert new_process.name() == "mongod"
    assert new_process.pid != process.pid
    assert new_process.is_running()


def test_no_start_mongo_server():
    """Если есть работающая MongoDB, то новая не запускается."""
    process_running = mongo_server._find_running_mongo_db()
    assert process_running is not None
    assert process_running.is_running()

    process = mongo_server.start_mongo_server()
    assert process.pid == process_running.pid
    assert process.is_running()
