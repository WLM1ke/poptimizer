"""Тесты для key-value хранилища на основе MongoDB."""
import pytest

from poptimizer.store import database


@pytest.fixture(scope="module", name="db")
def drop_test_db():
    """Создает и удаляет базу для тестирования."""
    db = database.MongoDB("test")
    yield db
    db.drop()


def test_mongodb_valid_data(db):
    """Проверка сохранения стандартного для MongoDB документа."""
    assert not db
    key_value = {"q": 1, "w": "text"}
    db["key"] = key_value
    assert db["key"] == key_value
    assert len(db) == 1

    del db["key"]  # noqa: WPS420
    assert db["key"] is None
    assert not db


def test_mongodb_not_valid_data(db):
    """Проверка сохранения нестандартного для MongoDB документа."""
    assert not db
    key_value = [{"q": 1, "w": "text"}]
    db["key2"] = key_value
    assert db["key2"] == key_value
    assert len(db) == 1

    del db["key2"]  # noqa: WPS420
    assert db["key2"] is None
    assert not db
