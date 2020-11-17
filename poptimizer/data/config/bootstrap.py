"""Конфигурация запуска приложения."""
import asyncio
import datetime
from typing import Final

from poptimizer.data.adapters import db
from poptimizer.data.app import handlers
from poptimizer.data.config import mongo_server, resources

# Настройки обработчика запросов к приложению
from poptimizer.data_di.app.bootstrap import START_DATE

_DB_SESSION = db.MongoDBSession(resources.MONGO_CLIENT["data"])
HANDLER: Final = handlers.Handler(asyncio.get_event_loop(), _DB_SESSION)

# Параметры налогов
TAX: Final = 0.13


def get_handler() -> handlers.Handler:
    """Обработчик запросов к приложению."""
    return HANDLER


def get_start_date() -> datetime.date:
    """Начальная дата для данных."""
    return START_DATE


def get_after_tax_rate() -> float:
    """1 минус ставка налога."""
    return 1 - TAX


mongo_server.prepare_mongo_db_server()
