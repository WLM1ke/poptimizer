"""Конфигурация запуска приложения."""
import asyncio
import datetime
from typing import Final

from poptimizer.data.adapters import db
from poptimizer.data.app import handlers
from poptimizer.data.domain import repo

# Настройки обработчика запросов к приложению
_DB_SESSION = db.MongoDBSession()


def _repo_factory() -> repo.Repo:
    """Создает репо."""
    return repo.Repo(_DB_SESSION)


_LOOP = asyncio.get_event_loop()
HANDLER = handlers.Handler(_LOOP, _repo_factory)


def get_handler() -> handlers.Handler:
    """Обработчик запросов к приложению."""
    return HANDLER


# Параметры представления конечных данных
# До 2015 года не у всех бумаг был режим T+2
# У некоторых бумаг происходило слияние без изменения тикера (IRAO)
_START_YEAR = 2015
START_DATE: Final = datetime.date(_START_YEAR, 1, 1)


def get_start_date() -> datetime.date:
    """Начальная дата для данных."""
    return START_DATE


# Параметры налогов
TAX = 0.13


def get_after_tax_rate() -> float:
    """1 минус ставка налога."""
    return 1 - TAX
