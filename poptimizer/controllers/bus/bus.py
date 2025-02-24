import aiohttp

from poptimizer.adapters import backup, mongo
from poptimizer.controllers.bus import events, msg, requests


def build(
    http_client: aiohttp.ClientSession,
    mongo_db: mongo.MongoDatabase,
) -> msg.Bus:
    repo = mongo.Repo(mongo_db)

    bus = msg.Bus(repo)
    bus.register_event_handler(backup.BackupHandler(repo), msg.IgnoreErrorsPolicy)
    events.register_handlers(bus, http_client)
    requests.register_handlers(bus)

    return bus
