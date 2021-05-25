"""Тесты для key-value хранилища на основе MongoDB."""
import pytest

from poptimizer.store import database


@pytest.fixture(scope="module", autouse=True)
def drop_test_db():
    """Создает и удаляет базу для тестирования."""
    database.MONGO_CLIENT.drop_database("test")
    yield
    database.MONGO_CLIENT.drop_database("test")


def test_mongodb_valid_data():
    """Проверка сохранения стандартного для MongoDB документа."""
    mongo = database.MongoDB("main", "test")

    assert not mongo
    key_value = {"q": 1, "w": "text"}
    mongo["key"] = key_value
    assert mongo["key"] == key_value
    assert len(mongo) == 1

    del mongo["key"]  # noqa: WPS420
    assert mongo["key"] is None
    assert not mongo


def test_mongodb_not_valid_data():
    """Проверка сохранения нестандартного для MongoDB документа."""
    mongo = database.MongoDB("main", "test")

    assert not mongo
    key_value = [{"q": 1, "w": "text"}]
    mongo["key2"] = key_value
    assert mongo["key2"] == key_value
    assert len(mongo) == 1

    del mongo["key2"]  # noqa: WPS420
    assert mongo["key2"] is None
    assert not mongo
