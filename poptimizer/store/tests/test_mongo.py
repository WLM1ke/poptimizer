import signal
import time

import pymongo
import requests

from poptimizer.store import mongo


def test_clean_up():
    assert mongo.MONGO_PROCESS.is_running()
    assert mongo.MONGO_CLIENT.nodes == frozenset({("localhost", 27017)})

    mongo.clean_up(mongo.MONGO_CLIENT, mongo.HTTP_SESSION)

    assert mongo.MONGO_CLIENT.nodes == frozenset()


def test_start_mongo_server():
    mongo_process = mongo.MONGO_PROCESS
    mongo_process.send_signal(signal.SIGTERM)
    mongo_process.wait()
    assert not mongo.MONGO_PROCESS.is_running()

    mongo.MONGO_PROCESS = mongo.start_mongo_server()
    time.sleep(1)
    assert mongo.MONGO_CLIENT.address == ("localhost", 27017)


def test_no_start_mongo_server():
    mongo_pid = mongo.MONGO_PROCESS.pid

    process = mongo.start_mongo_server()
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
