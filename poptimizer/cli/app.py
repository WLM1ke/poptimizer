import asyncio
import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import http_session, logger, mongo
from poptimizer.controllers.bus import bus
from poptimizer.controllers.server import server


async def _run() -> None:
    cfg = config.Cfg()
    err: Exception | None = None

    async with contextlib.AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(http_session.client())
        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))

        lgr = await stack.enter_async_context(
            logger.init(
                http_client,
                cfg.telegram_token,
                cfg.telegram_chat_id,
            )
        )

        msg_bus = bus.build(http_client, mongo_db)
        http_server = server.build(msg_bus, cfg.server_url)

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(msg_bus.run())
                tg.create_task(http_server.run())
        except asyncio.CancelledError:
            lgr.info("Shutdown finished")
        except Exception as exc:  # noqa: BLE001
            lgr.warning("Shutdown abnormally: %r", exc)
            err = exc

    if err:
        raise err


def run() -> None:
    """Run POptimizer.

    Can't be stopped with Ctrl-C/SIGINT. Settings from .env.
    """
    uvloop.run(_run())
