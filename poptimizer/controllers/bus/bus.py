import aiohttp

from poptimizer.adapters import backup, mongo
from poptimizer.controllers.bus import events, msg, requests
from poptimizer.use_cases import view


def build(
    http_client: aiohttp.ClientSession,
    mongo_db: mongo.MongoDatabase,
) -> msg.Bus:
    repo = mongo.Repo(mongo_db)
    viewer = view.Viewer(repo)

    bus = msg.Bus(repo)
    bus.register_event_handler(backup.BackupHandler(mongo_db), msg.IgnoreErrorsPolicy)
    events.register_handlers(bus, http_client, viewer)
    requests.register_handlers(bus)

    return bus
