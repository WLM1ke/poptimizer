"""Создает приложение для сбора данных."""
import aiohttp
from motor.motor_asyncio import AsyncIOMotorDatabase

from poptimizer.data import updater
from poptimizer.data.repo import Repo
from poptimizer.data.services import cpi, indexes, securities, trading_date


def data_app(mongo: AsyncIOMotorDatabase, session: aiohttp.ClientSession) -> updater.Updater:
    """Создает приложение для сбора данных."""
    repo = Repo(mongo)

    return updater.Updater(
        trading_date.Service(repo, session),
        cpi.Service(repo, session),
        indexes.Service(repo, session),
        securities.Service(repo, session),
    )
