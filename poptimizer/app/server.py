"""Создает http-сервер."""
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.app import config
from poptimizer.core import repository
from poptimizer.data.adapter import MarketData
from poptimizer.data.edit import dividends
from poptimizer.portfolio.edit import accounts, selected
from poptimizer.server import server


def create(
    cfg: config.Server,
    mongo_client: AsyncIOMotorClient,
) -> server.Server:
    """Создает сервер, показывающий SPA Frontend."""
    repo = repository.Repo(client=mongo_client)

    return server.Server(
        cfg.host,
        cfg.port,
        selected.Service(repo, MarketData(repo)),
        accounts.Service(repo),
        dividends.Service(repo),
    )
