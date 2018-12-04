"""Хранилище локальных данных."""
import pickle
from contextlib import AbstractContextManager
from typing import Any, Optional

import lmdb

from poptimizer import config

LMDB_SUBDIR = "lmdb"
# Предельный размер базы в байтах
MAX_DB_SIZE = 20 * 2 ** 20
# Максимальное число вложенных баз - в идеале должно вычисляться по количеству типов данных
MAX_DBS = 2  # TODO: Переделать на автоматическое вычисление


class DataStore(AbstractContextManager):
    """Сохраняет/загружает значение для указанного ключа и категории.

    Для каждого ключа можно сохранить несколько категорий значений ds[key, category]. Возможно сохранение
    значения без категории ds[key].

    Хранилище должно быть закрыто после использования методом close. Поддерживается автоматическое
    закрытие с помощью протокола контекстного менеджера. Если предполагается несколько операций,
    то для повышения скорости их следует осуществлять в рамках одной сессии, а не открывать/закрывать
    после каждой операции.
    """

    def __init__(self):
        self._env = lmdb.open(
            str(config.DATA_PATH / LMDB_SUBDIR), map_size=MAX_DB_SIZE, max_dbs=MAX_DBS
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            self.put(key[0], value, key[1])
        else:
            self.put(key, value)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            return self.get(*key)
        return self.get(key)

    def close(self):
        """Закрывает хранилище данных"""
        self._env.close()

    def _category_db(self, category, txn: lmdb.Transaction):
        """Возвращает базу данных для категории"""
        if category is None:
            return self._env.open_db(txn=txn, dupsort=False)
        return self._env.open_db(category.encode(), txn=txn, dupsort=False)

    def get(self, key: str, category: Optional[str] = None):
        """Получить данные из хранилища

        :param key:
            Ключ
        :param category:
            Необязательная категория
        :return:
            Значение
        """
        with self._env.begin(buffers=True) as txn:
            db = self._category_db(category, txn)
            raw_value = txn.get(key.encode(), db=db)
        return pickle.loads(raw_value)

    def put(self, key: str, value: Any, category: Optional[str] = None):
        """Поместить данные в хранилище

        :param key:
            Ключ
        :param category:
            Необязательная категория
        :param value:
            Данные
        """
        raw_value = pickle.dumps(value)
        with self._env.begin(write=True, buffers=True) as txn:
            db = self._category_db(category, txn)
            txn.put(key.encode(), raw_value, db=db)

    def stat(self, category: Optional[str] = None):
        """Статистические данные базы для категории

        :param category:
            Категория. None - категория по умолчанию.
        :return:
            Статистика в виде словаря:

            * psize	- размер страницы базыSize of a database page in bytes.
            * depth	- глубина B-деревьев.
            * branch_pages - количество внутренних страниц.
            * leaf_pages - количество листовых страниц.
            * overflow_pages - количество страниц с переполнением.
            * entries	- количество сохраненных данных.

        """
        with self._env.begin() as txn:
            db = self._category_db(category, txn)
            return txn.stat(db)
