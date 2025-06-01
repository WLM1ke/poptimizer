import asyncio
import logging
import traceback
from collections.abc import Coroutine

from poptimizer.adapters import logger


async def run(
    lgr: logging.Logger,
    *coroutines: Coroutine[None, None, None],
) -> int:
    try:
        async with asyncio.TaskGroup() as tg:
            for coroutine in coroutines:
                tg.create_task(coroutine)
    except asyncio.CancelledError:
        lgr.info("Shutdown finished gracefully")
    except Exception as exc:  # noqa: BLE001
        lgr.warning("Shutdown abnormally: %s", logger.get_root_error(exc))
        traceback.print_exception(exc, colorize=True)  # type: ignore[reportCallIssue]

        return 1

    return 0
