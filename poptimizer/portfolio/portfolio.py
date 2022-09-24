"""Создает объекты модуля работы с портфелем."""
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.core import repository, viewer
from poptimizer.portfolio.edit import selected
from poptimizer.portfolio.update import portfolio


def create_update_srv(mongo_client: AsyncIOMotorClient) -> portfolio.Service:
    """Создает сервис редактирования выбранных тикеров."""
    repo = repository.Repo(client=mongo_client)

    return portfolio.Service(repo, viewer.MarketData(repo))


def create_selected_srv(mongo_client: AsyncIOMotorClient) -> selected.Service:
    """Создает сервис редактирования выбранных тикеров."""
    repo = repository.Repo(client=mongo_client)

    return selected.Service(repo, viewer.MarketData(repo))
