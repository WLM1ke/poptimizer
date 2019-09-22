"""Абстрактный менеджер данных - предоставляет локальные данные и следит за их обновлением."""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Tuple

import numpy as np
import pandas as pd
import pymongo
import requests

from poptimizer.config import POptimizerError
from poptimizer.store import mongo, utils, database
from poptimizer.store.mongo import DB


class AbstractManager(ABC):
    """Организует создание, обновление и предоставление локальных данных."""

    # Момент времени после которого нужно обновление данных
    LAST_HISTORY_DATE = utils.get_last_history_date()

    def __init__(
        self,
        collection: str,
        db: str = DB,
        client: pymongo.MongoClient = mongo.MONGO_CLIENT,
        create_from_scratch: bool = False,
        validate_last: bool = True,
        index: str = utils.DATE,
        unique_index: bool = True,
        ascending_index: bool = True,
        session: requests.Session = mongo.HTTP_SESSION,
    ):
        """Данные хранятся в MongoDB и извлекаются в виде DataFrame.
        Сохраняемые данные представляются в виде следующего документа:
        {
            _id: str
            data: DataFrame.to_dict("records"),
            timestamp: datetime.datetime
        }
        :param collection:
            Коллекция в которой хранятся данные.
        :param db:
            База данных в которой хранятся данные.
        :param client:
            Подключенный клиент MongoDB.
        :param create_from_scratch:
            Нужно ли удалять данные при каждом обновлении.
        :param validate_last:
            Нужно ли при обновлении проверять только последнее значение или все значения.
        :param index:
            Наименование колонки для индекса.
        :param unique_index:
            Нужно ли тестировать индекс данных на уникальность.
        :param ascending_index:
            Нужно ли тестировать индекс данных на возрастание.
        :param session:
            Сессия для обновления данных по интернет.
        """
        self._mongo = database.MongoDB(collection, db, client)
        self._index = index
        self._create_from_scratch = create_from_scratch
        self._validate_last = validate_last
        self._unique_index = unique_index
        self._ascending_index = ascending_index
        self._session = session

    def __getitem__(self, item: str) -> pd.DataFrame:
        """Получение соответствующего элемента из базы."""
        doc = self._mongo[item]
        if doc is None:
            doc = self.create(item)
        elif doc["timestamp"] < self.LAST_HISTORY_DATE:
            if self._create_from_scratch:
                doc = self.create(item)
            else:
                doc = self.update(item, doc)
        if doc["data"]:
            df = pd.DataFrame(doc["data"]).set_index(self._index)
            self._validate_index(item, df)
            return df
        return pd.DataFrame()

    def _validate_index(self, item: str, df: pd.DataFrame):
        """Проверяет индекс данных с учетом настроек."""
        if self._unique_index and not df.index.is_unique:
            raise POptimizerError(
                f"Индекс {self._mongo.collection.full_name}.{item} не уникальный"
            )
        if self._ascending_index and not df.index.is_monotonic_increasing:
            raise POptimizerError(
                f"Индекс {self._mongo.collection.full_name}.{item} не возрастает"
            )

    def create(self, item: str) -> Dict[str, Any]:
        """Создает локальные данные с нуля или перезаписывает существующие."""
        logging.info(f"Создание данных {self._mongo.collection.full_name}.{item}")
        data = self._download(item, None)
        doc = dict(data=data, timestamp=datetime.utcnow())
        self._mongo[item] = doc
        logging.info(f"Данные обновлены {self._mongo.collection.full_name}.{item}")
        return doc

    def update(self, item: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет локальные данные.

        Во время обновления проверяется стыковку новых данных с существующими.
        """
        data = doc["data"]
        if data:
            last_index = data[-1][self._index]
        else:
            last_index = None
        logging.info(f"Обновление данных {self._mongo.collection.full_name}.{item}")
        data_new = self._download(item, last_index)
        self._validate_new(item, data, data_new)
        if self._validate_last:
            data_new = data + data_new[1:]
        doc = dict(data=data_new, timestamp=datetime.utcnow())
        self._mongo[item] = doc
        logging.info(f"Данные обновлены {self._mongo.collection.full_name}.{item}")
        return doc

    def _validate_new(
        self, item: str, data: List[Dict[str, Any]], data_new: List[Dict[str, Any]]
    ):
        """Проверяет соответствие старых и новых данных."""
        if self._validate_last:
            data = data[-1:]
            data_new = data_new[:1]
        elif len(data) > len(data_new):
            raise POptimizerError(
                f"Новые {len(data_new)} короче старых {len(data)} данных "
                f"{self._mongo.collection.full_name}.{item}"
            )
        for old, new in zip(data, data_new):
            for col in old:
                not_float_not_eq = (
                    not isinstance(old[col], float) and old[col] != new[col]
                )
                float_not_eq = isinstance(old[col], float) and not np.allclose(
                    old[col], new[col]
                )
                if not_float_not_eq or float_not_eq:
                    raise POptimizerError(
                        f"Новые {new} не соответствуют старым {old} данным "
                        f"{self._mongo.collection.full_name}.{item}"
                    )

    @abstractmethod
    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        """Загружает необходимые данные из внешних источников.
        :param item:
            Наименования данных.
        :param last_index:
            Если None, то скачиваются все данные. Если присутствует последние значение индекса,
            то для ускорения данные загружаются начиная с этого значения для инкрементального обновления.
        :return:
            Список словарей в формате DataFrame.to_dict("records").
        """


def data_formatter(
    data: List[Dict[str, Any]], formatters: Dict[str, Callable[[Any], Tuple[str, Any]]]
) -> List[Dict[str, Any]]:
    """Форматирует данные с учетом установок.
    :param data:
        Список словарей в формате DataFrame.to_dict("records").
    :param formatters:
        Словарь с функциями форматирования.
    :return:
       Отформатированный список словарей в формате.
    """
    for row in data:
        for col, formatter in formatters.items():
            new_col, value = formatter(row.pop(col))
            row[new_col] = value
    return data
