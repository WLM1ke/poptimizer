import uvloop

from poptimizer import config
from poptimizer.adapters import message, uow
from poptimizer.data import day_started
from poptimizer.io import mongo


async def _run() -> None:
    cfg = config.Cfg()

    async with (
        mongo.client(cfg.mongo_client.uri) as mongo_client,
        message.Bus(uow.UOWFactory(mongo_client)) as bus,
    ):
        bus.add_event_publisher(day_started.DayStartedPublisher())


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
