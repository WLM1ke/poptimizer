import logging
import signal
import time

import pymongo
import pytest
import requests

from poptimizer.store import mongo


def test_no_start_mongo_server(caplog):
    mongo_pid = mongo.MONGO_PROCESS.pid
    with caplog.at_level(logging.INFO):
        process = mongo.start_mongo_server()
    assert "Локальный сервер MongoDB уже работает" in caplog.text
    assert process.pid == mongo_pid
    assert process.is_running()


def test_start_mongo_client():
    with mongo.start_mongo_client() as client:
        assert isinstance(client, pymongo.MongoClient)
        assert client.address == ("localhost", 27017)
        assert client.codec_options.tz_aware is False


@pytest.fixture("function")
def shutdown_mongo_server():
    mongo_process = mongo.MONGO_PROCESS
    mongo_process.send_signal(signal.SIGTERM)
    mongo_process.wait()


@pytest.mark.usefixtures("shutdown_mongo_server")
def test_start_mongo_server(caplog):
    assert not mongo.MONGO_PROCESS.is_running()

    with caplog.at_level(logging.INFO):
        mongo.MONGO_PROCESS = mongo.start_mongo_server()
    assert "Запускается локальный сервер MongoDB" in caplog.text
    time.sleep(1)
    assert mongo.MONGO_CLIENT.address == ("localhost", 27017)


def test_start_http_session():
    with mongo.start_http_session() as session:
        assert isinstance(session, requests.Session)


def test_clean_up(caplog):
    assert mongo.MONGO_PROCESS.is_running()
    assert mongo.MONGO_CLIENT.nodes == frozenset({("localhost", 27017)})

    with caplog.at_level(logging.INFO):
        mongo.clean_up(mongo.MONGO_PROCESS)

    assert "Подключение клиента MongoDB закрыто" in caplog.text
    assert mongo.MONGO_CLIENT.nodes == frozenset()

    assert "Локальный сервер MongoDB остановлен со статусом 0" in caplog.text
    assert not mongo.MONGO_PROCESS.is_running()

    assert "Сессия для обновления данных по интернет закрыта" in caplog.text
