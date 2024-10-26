import aiohttp

from poptimizer.adapters import mongo
from poptimizer.controllers.bus import events, msg, requests


def build(
    http_client: aiohttp.ClientSession,
    mongo_db: mongo.MongoDatabase,
) -> msg.Bus:
    repo = mongo.Repo(mongo_db)
    bus = msg.Bus(repo)

    events.register_handlers(bus, http_client, mongo_db)
    requests.register_handlers(bus)

    return bus
