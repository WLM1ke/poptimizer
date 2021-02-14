"""Тесты базовых классов взаимодействия с внешней инфраструктурой."""
import asyncio
import logging
import random

import pytest

from poptimizer.shared import adapters, domain

TEST_ID = domain.ID("a", "b", "c")
TEST_ENTITY = domain.BaseEntity(TEST_ID)


class TestLog:
    """Тестовый класс для проверки работы логгера."""

    logger = adapters.AsyncLogger()


@pytest.mark.asyncio
async def test_async_logger(caplog):
    """Работа и автоматическое присвоение имени асинхронному логгеру."""
    caplog.set_level(logging.INFO)

    test_obj = TestLog()

    test_obj.logger("test_message")

    await asyncio.sleep(0.01)

    assert caplog.record_tuples == [("TestLog", 20, "test_message")]


@pytest.fixture(scope="function", name="mapper")
def create_mapper(mocker):
    """Создает мэппер."""
    desc = (
        adapters.Desc("aa", "bb", "cc", str, int),
        adapters.Desc("dd", "dd", "dd"),
        adapters.Desc("ff", "ff", "ff"),
    )
    return adapters.Mapper(desc, mocker.MagicMock(), mocker.AsyncMock())


async def fake_get_doc(_):
    """Возвращает пустой словарь со случайной задержкой."""
    await asyncio.sleep(random.random())  # noqa: S311
    return {}


class FakeDecode:
    """Декодер для тестов."""

    def __init__(self, first, second):
        """Создает объекты по двум аргументам."""


@pytest.mark.asyncio
async def test_get_concurrent_identity(mapper):
    """При конкурентном доступе возвращается один и тот же объект."""
    mapper.get_doc = fake_get_doc
    mapper._decode = FakeDecode
    object_gets = [mapper.__call__(TEST_ID) for _ in range(100)]
    first, *others = await asyncio.gather(*object_gets)

    last = await mapper.__call__(TEST_ID)

    for loaded_objects in others:
        assert first is loaded_objects

    assert last is first


@pytest.mark.asyncio
async def test_get_doc(mocker, mapper):
    """Загрузка документа."""
    fake_collection = mocker.AsyncMock()
    mocker.patch.object(mapper, "_get_collection_and_id", return_value=(fake_collection, "name"))
    fake_collection.find_one.return_value = mocker.sentinel

    assert await mapper.get_doc(TEST_ID) is mocker.sentinel

    mapper._get_collection_and_id.assert_called_once_with(TEST_ID)
    fake_collection.find_one.assert_called_once_with({"_id": "name"}, projection={"_id": False})


@pytest.mark.asyncio
async def test_get_doc_for_none_doc(mocker, mapper):
    """Создание пустого словаря при отсутствии документа."""
    fake_collection = mocker.AsyncMock()
    mocker.patch.object(mapper, "_get_collection_and_id", return_value=(fake_collection, "name"))
    fake_collection.find_one.return_value = None

    rez = await mapper.get_doc(TEST_ID)
    assert isinstance(rez, dict)
    assert not rez

    mapper._get_collection_and_id.assert_called_once_with(TEST_ID)
    fake_collection.find_one.assert_called_once_with({"_id": "name"}, projection={"_id": False})


@pytest.mark.asyncio
async def test_commit(mocker, mapper):
    """Сохранение объекта."""
    encoder_rez = {"df": "value"}
    fake_collection = mocker.AsyncMock()
    mocker.patch.object(mapper, "_get_collection_and_id", return_value=(fake_collection, "name"))
    mocker.patch.object(mapper, "_encode", return_value=encoder_rez)

    await mapper.commit(TEST_ENTITY)

    mapper._encode.assert_called_once_with(TEST_ENTITY)
    mapper._get_collection_and_id.assert_called_once_with(TEST_ID)
    fake_collection._encode.replace_one(
        filter={"_id": "c"},
        replacement={"_id": "c", "df": "value"},
        upsert=True,
    )


@pytest.mark.asyncio
async def test_commit_no_change(mocker, mapper):
    """Пропуск сохранения не измененного объекта."""
    encoder_rez = {}
    fake_collection = mocker.AsyncMock()
    mocker.patch.object(mapper, "_get_collection_and_id", return_value=(fake_collection, "name"))
    mocker.patch.object(mapper, "_encode", return_value=encoder_rez)

    await mapper.commit(TEST_ENTITY)

    mapper._encode.assert_called_once_with(TEST_ENTITY)
    assert not mapper._get_collection_and_id.call_count
    assert not fake_collection._encode.replace_one.call_count


NAME_CASES = (
    (TEST_ID, ("a", "b", "c")),
    (domain.ID("a", "c", "c"), ("a", adapters.MISC, "c")),
)


@pytest.mark.parametrize("id_, rez", NAME_CASES)
def test_get_collection_and_id(mapper, id_, rez):
    """Тестирование комбинации двух случаев - с/без специальной коллекцией."""
    collection, name = mapper._get_collection_and_id(id_)

    db = mapper._client.__getitem__
    db.assert_called_once_with(rez[0])
    db.return_value.__getitem__.assert_called_once_with(rez[1])
    assert db.return_value.__getitem__.return_value == collection
    assert name == rez[2]


def test_encode_no_change(mapper):
    """Возврат пустого словаря для не измененного объекта."""
    state = mapper._encode(TEST_ENTITY)
    assert isinstance(state, dict)
    assert not state


def test_encode_changed(mapper):
    """Возврат возврат декодированных изменений и сброс статуса изменений у объекта."""
    entity = domain.BaseEntity(TEST_ID)
    entity.aa = 1
    entity.aa = 2

    entity.dd = 1
    entity.dd = 2

    assert mapper._encode(entity) == {"bb": "2", "dd": 2}
    assert not entity.changed_state()


def test_decode(mapper):
    """Возврат пустого словаря для не измененного объекта."""
    assert mapper._decode(TEST_ID, {"bb": "2", "dd": 2}) == mapper._factory.return_value

    mapper._factory.assert_called_once_with(TEST_ID, {"cc": 2, "dd": 2})
