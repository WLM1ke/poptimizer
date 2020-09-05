"""Конфигурация запуска приложения."""
import asyncio
import datetime
from typing import Final

from motor import motor_asyncio

from poptimizer.data.adapters import db
from poptimizer.data.app import handlers

# Настройки MongoDB
_MONGO_URI = "mongodb://localhost:27017"
_CLIENT = motor_asyncio.AsyncIOMotorClient(_MONGO_URI, tz_aware=False)


# Настройки обработчика запросов к приложению
_DB = _CLIENT["data_new"]
_DB_SESSION = db.MongoDBSession(_DB)
_LOOP = asyncio.get_event_loop()
HANDLER = handlers.Handler(_LOOP, _DB_SESSION)


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
