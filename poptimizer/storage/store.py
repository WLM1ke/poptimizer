"""Хранилище локальных данных"""
import pickle
from contextlib import AbstractContextManager
from typing import Any

import lmdb

from poptimizer import config

LMDB_SUBDIR = "lmdb"
# Максимальное число вложенных баз - в иделае должно вычисляться по количеству типов данных
MAX_DBS = 2  # TODO: Переделать на автоматическое вычисление


class DataStore(
    AbstractContextManager
):  # TODO: после использования посмотреть статистику базы
    """Сохраняет/загружает значение для указанноых наименования и категории данных"""

    def __init__(self):
        self._env = lmdb.open(str(config.DATA_PATH / LMDB_SUBDIR), max_dbs=MAX_DBS)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __setitem__(self, key, value):
        self.put(*key, value)

    def __getitem__(self, key):
        return self.get(*key)

    def close(self):
        """Закрывает хранилище данных"""
        self._env.close()

    def _category_db(self, category, txn: lmdb.Transaction):
        """Возвращает базу данных для категории"""
        if category is None:
            return self._env.open_db(txn=txn, dupsort=False)
        return self._env.open_db(category.encode(), txn=txn, dupsort=False)

    def get(self, category: str, name: str):
        """Получить данные из хранилища

        :param category:
            Категория данных
        :param name:
            Наименование данных
        :return:
            Исходные данные
        """
        with self._env.begin() as txn:
            db = self._category_db(category, txn)
            raw_value = txn.get(name.encode(), db=db)
        return pickle.loads(raw_value)

    def put(self, category: str, name: str, value: Any):
        """Поместить данные в хранилищке

        :param category:
            Категория данных
        :param name:
            Наименование данных
        :param value:
            Данные
        """
        raw_value = pickle.dumps(value)
        with self._env.begin(write=True) as txn:
            db = self._category_db(category, txn)
            txn.put(name.encode(), raw_value, db=db)
