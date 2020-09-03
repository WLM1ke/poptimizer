"""Конфигурация приложения."""
import datetime
from typing import Final

from poptimizer.data.adapters import db
from poptimizer.data.app import services
from poptimizer.data.domain import repo

_DB_SESSION = db.MongoDBSession()


def repo_factory() -> repo.Repo:
    """Создает репо."""
    return repo.Repo(_DB_SESSION)


# Параметры для инициализации обработчиков на уровне приложения
EVENTS_BUS = services.EventsBus(repo_factory)
VIEWER = services.Viewer(repo_factory)

# Параметры представления конечных данных
_START_YEAR = 2015
START_DATE: Final = datetime.date(_START_YEAR, 1, 1)
