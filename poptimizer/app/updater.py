"""Создает сервис обновления данных."""
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.core import backup, repository
from poptimizer.data import updater
from poptimizer.data.adapter import MarketData
from poptimizer.data.update import cpi, divs, indexes, quotes, securities, trading_date, usd
from poptimizer.data.update.raw import check_raw, nasdaq, reestry, status
from poptimizer.portfolio.adapter import PortfolioData
from poptimizer.portfolio.update import portfolio


def create(mongo_client: AsyncIOMotorClient, session: aiohttp.ClientSession) -> updater.Updater:
    """Создает сервис обновления данных."""
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
        status.Service(repo, session, PortfolioData(repo)),
        reestry.Service(repo, session),
        nasdaq.Service(repo, session),
        check_raw.Service(repo),
        portfolio.Service(repo, MarketData(repo)),
    )
