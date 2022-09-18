"""Создает приложение для сбора данных и сервисы для их редактирования."""
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.core import backup, repository
from poptimizer.data import updater
from poptimizer.data.edit import dividends, selected
from poptimizer.data.update import cpi, divs, indexes, quotes, securities, trading_date, usd
from poptimizer.data.update.raw import check_raw, nasdaq, reestry, status


def create_app(mongo_client: AsyncIOMotorClient, session: aiohttp.ClientSession) -> updater.Updater:
    """Создает приложение для сбора данных."""
    repo = repository.Repo(mongo_client)

    return updater.Updater(
        backup.Service(mongo_client),
        trading_date.Service(repo, session),
        cpi.Service(repo, session),
        indexes.Service(repo, session),
        securities.Service(repo, session),
        quotes.Service(repo, session),
        usd.Service(repo, session),
        divs.Service(repo),
        status.Service(repo, session),
        reestry.Service(repo, session),
        nasdaq.Service(repo, session),
        check_raw.Service(repo),
    )


def create_selected_srv(mongo_db: AsyncIOMotorClient) -> selected.Service:
    """Создает сервис редактирования выбранных тикеров."""
    return selected.Service(repository.Repo(client=mongo_db))


def create_dividends_srv(mongo_db: AsyncIOMotorClient) -> dividends.Service:
    """Создает сервис редактирования дивидендов."""
    return dividends.Service(repository.Repo(client=mongo_db))
