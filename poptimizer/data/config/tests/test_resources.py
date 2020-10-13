"""Тесты общих ресурсов для загрузки и сохранения данных."""
import aiohttp
from motor import motor_asyncio

from poptimizer.data.config import resources


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
