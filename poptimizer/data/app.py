"""Создает приложение для сбора данных и сервисы редактирования для их редактирования."""
import aiohttp
from motor.motor_asyncio import AsyncIOMotorDatabase

from poptimizer.data import backup, updater
from poptimizer.data.edit import selected
from poptimizer.data.repo import Repo
from poptimizer.data.update import cpi, indexes, securities, trading_date
from poptimizer.data.update.raw import check_raw, nasdaq, reestry, status


def create_app(mongo_db: AsyncIOMotorDatabase, session: aiohttp.ClientSession) -> updater.Updater:
    """Создает приложение для сбора данных."""
    repo = Repo(mongo_db)

    return updater.Updater(
        backup.Service(mongo_db),
        trading_date.Service(repo, session),
        cpi.Service(repo, session),
        indexes.Service(repo, session),
        securities.Service(repo, session),
        status.Service(repo, session),
        reestry.Service(repo, session),
        nasdaq.Service(repo, session),
        check_raw.Service(repo),
    )


def create_selected_srv(mongo_db: AsyncIOMotorDatabase) -> selected.Service:
    """Создает сервис редактирования выбранных тикеров."""
    return selected.Service(Repo(db=mongo_db))
