"""Создает приложение для сбора данных."""
import aiohttp
from motor.motor_asyncio import AsyncIOMotorCollection

from poptimizer.data import updater
from poptimizer.data.cpi import CPISrv
from poptimizer.data.repo import Repo
from poptimizer.data.trading_day import DatesSrv


def data_app(mongo: AsyncIOMotorCollection, session: aiohttp.ClientSession) -> updater.Updater:
    """Создает приложение для сбора данных."""
    repo = Repo(mongo)

    dates_srv = DatesSrv(repo, session)
    cpi_srv = CPISrv(repo, session)

    return updater.Updater(dates_srv, cpi_srv)
