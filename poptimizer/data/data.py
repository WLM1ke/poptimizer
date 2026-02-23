import asyncio
from typing import Any

import aiohttp

from poptimizer.core import actors
from poptimizer.data import actor
from poptimizer.data.clients import data, memory, migration


def build_actor(
    task_to_cancel: asyncio.Task[Any] | None,
    http_client: aiohttp.ClientSession,
) -> actors.Actor[Any, Any]:
    memory_client = memory.Checker(task_to_cancel)
    migration_client = migration.Client()
    data_client = data.Client(http_client)

    return actor.DataActor(
        memory_client,
        migration_client,
        data_client,
        actors.AID(""),
    )
