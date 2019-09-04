"""Абстрактный менеджер данных - предоставляет локальные данные и следит за их обновлением."""
import logging
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, Callable

import pandas as pd
import pymongo
import requests

from poptimizer import config
from poptimizer.config import POptimizerError
from poptimizer.store import DATE

COMMAND = [
    "mongod",
    "--logpath",
    config.MONGO_LOG_PATH,
    "--quiet",
    "--dbpath",
    config.MONGO_PATH,
    "--bind_ip",
    "127.0.0.1",
]
subprocess.Popen(COMMAND, stdout=subprocess.DEVNULL)

SESSION = requests.Session()
MONGO = pymongo.MongoClient("localhost", 27017, tz_aware=False)


class AbstractManager(ABC):
    """Организует создание, обновление и предоставление локальных данных."""

    def __init__(
        self,
        names: Tuple[str, ...],
        collection: str,
        db: str = "data",
        client: pymongo.MongoClient = MONGO,
        create_from_scratch: bool = False,
        index: str = DATE,
        unique_index: bool = True,
        monotonic_index: bool = True,
        session: requests.Session = SESSION,
    ):
        """Данные хранятся в MongoDB и извлекаются в виде DataFrame.

        Сохраняемые данные представляются в виде следующего документа:
        {
            _id: str
            data: DataFrame.to_dict(orient="records"),
            last_update: datetime.datetime
        }

        :param names:
            Наименования данных.
        :param collection:
            Коллекция в которой хранятся данные.
        :param db:
            База данных в которой хранятся данные.
        :param client:
            Подключенный клиент MongoDB.
        :param create_from_scratch:
            Нужно ли удалять данные при каждом обновлении.
        :param index:
            Наименование колонки для индекса.
        :param unique_index:
            Нужно ли тестировать индекс данных на уникальность.
        :param monotonic_index:
            Нужно ли тестировать индекс данных на монотонность.
        :param session:
            Сессия для обновления данных по интернет.
        """
        self._names = list(names)
        self._collection = client[db][collection]
        self._index = index
        self._create_from_scratch = create_from_scratch
        self._unique_index = unique_index
        self._monotonic_index = monotonic_index
        self._session = session

    def load(self) -> Dict[str : pd.DataFrame]:
        """Загружает данные без обновления."""
        result = self._collection.find({"_id": {"$in": self._names}}, ["_id", "data"])
        return {
            doc["_id"]: pd.DataFrame(doc["data"]).set_index(self._index)
            for doc in result
        }

    def create(self, name) -> None:
        """Создает локальные данные с нуля или перезаписывает существующие.

        При необходимости индекс данных проверяется на уникальность и монотонность.

        :param name:
            Наименование данных.
        """
        logging.info(f"Создание локальных данных {self._collection.name} -> {name}")
        data = self._download(name, None)
        self._validate_index(name, data)
        data = dict(_id=name, data=data, last_update=datetime.utcnow())
        result = self._collection.replace_one({"_id": name}, data, upsert=True)
        print(result)
        if result.modified_count == 1:
            logging.info(f"Данные обновлены {self._collection.name} -> {name}")

    def _validate_index(self, name: str, data):
        """Проверяет индекс данных с учетом настроек."""
        if self.IS_UNIQUE and not data.index.is_unique:
            raise POptimizerError(f"Индекс {name} не уникальный")
        if self.IS_MONOTONIC and not data.index.is_monotonic_increasing:
            raise POptimizerError(f"Индекс {name} не возрастает монотонно")

    def update(self) -> None:
        """Обновляет данных."""

    def get(self) -> pd.DataFrame:
        """При необходимости обновляет данные и загружает их."""

    @abstractmethod
    def _download(
        self, name: str, last_date: Optional[pd.Timestamp]
    ) -> List[Dict[str:Any]]:
        """Загружает необходимые данные из внешних источников.

        :param name:
            Наименования данных.
        :param last_date:
            Если None, то скачиваются все данные. Если присутствует конкретная дата, то для ускорения
            загрузки загружаются данные начиная с этой даты для инкрементального обновления.
        :return:
            Список словарей в формате DataFrame.to_dict(orient="records").
        """

    @staticmethod
    def _format(
        data: List[Dict[str:Any]], formatters: Dict[str:Callable]
    ) -> List[Dict[str:Any]]:
        """Форматирует данные с учетом установок.

        :param data:
            Список словарей в формате DataFrame.to_dict(orient="records").
        :param formatters:
            Словарь с функциями форматирования.
        :return:
           Отформатированный список словарей в формате.
        """
        for row in data:
            for col, formatter in formatters:
                row[col] = formatter(row[col])
        return data
