import logging
import subprocess
import time

import psutil
import pymongo
import requests

from poptimizer.store import mongo


def test_clean_up(caplog):
    assert mongo.MONGO_PROCESS.is_running()
    assert mongo.MONGO_CLIENT.nodes == frozenset({("localhost", 27017)})

    with caplog.at_level(logging.INFO):
        mongo.clean_up(mongo.MONGO_CLIENT, mongo.HTTP_SESSION)

    assert "Подключение клиента MongoDB закрыто" in caplog.text
    assert mongo.MONGO_CLIENT.nodes == frozenset()

    assert "Сессия для обновления данных по интернет закрыта" in caplog.text


def test_start_mongo_server(caplog):
    stop_server = ["pkill", "-x", "mongod"]
    psutil.Popen(stop_server, stdout=subprocess.DEVNULL)
    time.sleep(1)
    assert not mongo.MONGO_PROCESS.is_running()

    with caplog.at_level(logging.INFO):
        mongo.MONGO_PROCESS = mongo.start_mongo_server()
    assert "Запускается локальный сервер MongoDB" in caplog.text
    time.sleep(1)
    assert mongo.MONGO_CLIENT.address == ("localhost", 27017)


def test_no_start_mongo_server(caplog):
    mongo_pid = mongo.MONGO_PROCESS.pid
    with caplog.at_level(logging.INFO):
        process = mongo.start_mongo_server()
    assert "Локальный сервер MongoDB уже работает" in caplog.text
    assert process.pid == mongo_pid
    assert process.is_running()


def test_start_mongo_client():
    mongo.MONGO_CLIENT = mongo.start_mongo_client(mongo.HTTP_SESSION)
    assert isinstance(mongo.MONGO_CLIENT, pymongo.MongoClient)
    assert mongo.MONGO_CLIENT.address == ("localhost", 27017)
    assert mongo.MONGO_CLIENT.codec_options.tz_aware is False


def test_start_http_session():
    mongo.HTTP_SESSION = mongo.start_http_session()
    assert isinstance(mongo.HTTP_SESSION, requests.Session)
