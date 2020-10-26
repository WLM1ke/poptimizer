"""Конфигурация внешней инфраструктуры."""
from typing import Final

import aiohttp
import injector

from poptimizer.data.adapters import logger
from poptimizer.data_di.adapters import http

POOL_SIZE: Final = 20


class Adapters(injector.Module):
    """Конфигурация внешней инфраструктуры."""

    def configure(self, binder: injector.Binder) -> None:
        """Построение конфигурация внешней инфраструктуры."""
        binder.bind(aiohttp.ClientSession, to=http.http_session_factory(POOL_SIZE))
        binder.bind(logger.AsyncLogger, to=logger.AsyncLogger("GateWays"))
