import asyncio
import logging
from collections.abc import Coroutine


async def run(lgr: logging.Logger, *coroutines: Coroutine[None, None, None]) -> None:
    err: Exception | None = None

    try:
        async with asyncio.TaskGroup() as tg:
            for coroutine in coroutines:
                tg.create_task(coroutine)
    except asyncio.CancelledError:
        lgr.info("Stopped")
    except Exception as exc:  # noqa: BLE001
        lgr.warning("Shutdown abnormally: %r", exc)
        err = exc

    if err:
        raise err
