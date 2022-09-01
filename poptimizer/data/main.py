"""Создает приложение для сбора данных."""
import aiohttp
from motor.motor_asyncio import AsyncIOMotorCollection

from poptimizer.data import updater
from poptimizer.data.repo import Repo
from poptimizer.data.services import cpi, indexes, trading_day


def data_app(mongo: AsyncIOMotorCollection, session: aiohttp.ClientSession) -> updater.Updater:
    """Создает приложение для сбора данных."""
    repo = Repo(mongo)

    return updater.Updater(
        trading_day.Service(repo, session),
        cpi.Service(repo, session),
        indexes.Service(repo, session),
    )
