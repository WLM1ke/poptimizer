"""Конфигурация запуска приложения."""
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


HANDLER = handlers.Handler(_repo_factory)


def get_handler() -> handlers.Handler:
    """Обработчик запросов к приложению."""
    return HANDLER


# Параметры представления конечных данных
_START_YEAR = 2015
START_DATE: Final = datetime.date(_START_YEAR, 1, 1)


def get_start_date() -> datetime.date:
    """Начальная дата для данных."""
    return START_DATE
