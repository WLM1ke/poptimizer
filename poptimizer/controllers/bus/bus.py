from collections.abc import Callable
from typing import TYPE_CHECKING

from poptimizer.adapters import backup, mongo
from poptimizer.controllers.bus import events, msg, requests

if TYPE_CHECKING:
    import aiohttp


def build(
    http_client: aiohttp.ClientSession,
    mongo_db: mongo.MongoDatabase,
    stop_fn: Callable[[], bool] | None,
) -> msg.Bus:
    repo = mongo.Repo(mongo_db)

    bus = msg.Bus(repo)
    bus.register_event_handler(backup.BackupHandler(repo), msg.IgnoreErrorsPolicy)
    events.register_handlers(bus, http_client, stop_fn)
    requests.register_handlers(bus)

    return bus
