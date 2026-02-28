import asyncio
import signal
from types import FrameType
from typing import Any, Final

import psutil

from poptimizer.core import fsms

_MEMORY_PERCENTAGE_THRESHOLD: Final = 75


class _SignalHandler:
    def __init__(self, task: asyncio.Task[Any]) -> None:
        self._task = task

    def __call__(self, sig: int, frame: FrameType | None) -> None:  # noqa: ARG002
        self._task.cancel()


class Checker:
    def __init__(
        self,
        task_to_cancel: asyncio.Task[Any] | None,
        percentage_threshold: int = _MEMORY_PERCENTAGE_THRESHOLD,
    ) -> None:
        self._percentage_threshold = percentage_threshold
        self._task_to_cancel = task_to_cancel

        if self._task_to_cancel:
            signal.signal(signal.SIGTERM, _SignalHandler(self._task_to_cancel))

    def check_memory_usage(self, ctx: fsms.Ctx) -> None:
        if not self._task_to_cancel:
            return

        match (usage := psutil.virtual_memory().percent) > self._percentage_threshold:
            case True:
                ctx.info("Stopping due to high memory usage - %.2f%%", usage)
                self._task_to_cancel.cancel()
            case False:
                ctx.info("Memory usage - %.2f%%", usage)
