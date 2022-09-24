"""Создает приложение для сбора данных и сервисы для их редактирования."""
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.core import backup, repository, viewer
from poptimizer.data import updater
from poptimizer.data.edit import dividends
from poptimizer.data.update import cpi, divs, indexes, quotes, securities, trading_date, usd
from poptimizer.data.update.raw import check_raw, nasdaq, reestry, status
from poptimizer.portfolio import portfolio


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
        status.Service(repo, session, viewer.Portfolio(repo)),
        reestry.Service(repo, session),
        nasdaq.Service(repo, session),
        check_raw.Service(repo),
        portfolio.create_update_srv(mongo_client),
    )


def create_dividends_srv(mongo_db: AsyncIOMotorClient) -> dividends.Service:
    """Создает сервис редактирования дивидендов."""
    return dividends.Service(repository.Repo(client=mongo_db))
