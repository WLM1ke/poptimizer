import logging
import time

import pymongo
import pytest
import requests
from pymongo.errors import AutoReconnect, ServerSelectionTimeoutError

from poptimizer.store import mongo


def test_start_mongo_client():
    with mongo.start_mongo_client() as client:
        assert isinstance(client, pymongo.MongoClient)
        assert client.address == ("localhost", 27017)
        assert client.codec_options.tz_aware is False
        assert client.server_selection_timeout == 1.0


def test_no_start_mongo_server(caplog):
    client = mongo.DB_CLIENT
    mongo_pid = mongo.MONGO_PROCESS.pid
    with caplog.at_level(logging.INFO):
        process = mongo.start_mongo_server(client)
    assert "Локальный сервер MongoDB уже работает" in caplog.text
    assert process.pid == mongo_pid


@pytest.fixture("function")
def shutdown_mongo_server():
    client = mongo.DB_CLIENT
    try:
        admin = client["admin"]
        admin.command("shutdown")
    except AutoReconnect:
        pass


@pytest.mark.usefixtures("shutdown_mongo_server")
def test_start_mongo_server(caplog):
    client = mongo.DB_CLIENT
    with pytest.raises(ServerSelectionTimeoutError) as error:
        client["admin"].command("serverStatus")
    assert error.type == ServerSelectionTimeoutError
    assert "localhost:27017: [Errno 61] Connection refused" in str(error.value)

    with caplog.at_level(logging.INFO):
        mongo.MONGO_PROCESS = mongo.start_mongo_server(client)
    assert "Запускается локальный сервер MongoDB" in caplog.text
    time.sleep(1)
    assert client.address == ("localhost", 27017)


def test_start_http_session():
    with mongo.start_http_session() as session:
        assert isinstance(session, requests.Session)


def test_clean_up(caplog):
    assert mongo.MONGO_PROCESS.is_running()
    assert mongo.DB_CLIENT.nodes == frozenset({("localhost", 27017)})

    with caplog.at_level(logging.INFO):
        mongo.clean_up(mongo.MONGO_PROCESS)

    assert "Локальный сервер MongoDB остановлен со статусом 0" in caplog.text
    assert not mongo.MONGO_PROCESS.is_running()

    assert "Подключение клиента MongoDB закрыто" in caplog.text
    assert mongo.DB_CLIENT.nodes == frozenset()

    assert "Сессия для обновления данных по интернет закрыта" in caplog.text
