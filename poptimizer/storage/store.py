"""Хранилище локальных данных."""
import pathlib
import pickle
from contextlib import AbstractContextManager
from typing import Any, Optional, Union

import lmdb


class DataStore(AbstractContextManager):
    """Сохраняет/загружает значение для указанного ключа и категории.

    Для каждого ключа можно сохранить несколько категорий значений ds[key, category]. Возможно сохранение
    значения без категории ds[key].

    Хранилище должно быть закрыто после использования методом close. Поддерживается автоматическое
    закрытие с помощью протокола контекстного менеджера. Если предполагается несколько операций,
    то для повышения скорости их следует осуществлять в рамках одной сессии, а не открывать/закрывать
    после каждой операции.
    """

    def __init__(
        self, path: Union[str, pathlib.Path], max_size=10 * 2 ** 20, categories=0
    ):
        """Создается база в указанном каталоге (два файла: база и лок-файл).

        Размер по умолчанию небольшой, обычно требуется больший. Кроме того при множестве обращений база
        может временно вырастать до размеров, существенно превышающих объем хранимых данных, поэтому
        максимальный размер должен выбираться с запасом.

        При использовании более 0 категорий в основной базе создаются вложенные базы, для каждой из
        которых в основной базе формируется специальный ключ с названием категории, который не должен
        дублироваться с обычными ключами в основной базе. Если категорий 0, то будет использоваться одна
        основная база для категории по умолчанию.

        :param path:
            Путь к каталогу с базой - если база отсутствует, то она будет создана, а путь полностью
            проложен.
        :param max_size:
            Максимальный размер базы. По умолчанию 10МБ.
        :param categories:
            Количество вложенных баз для категорий.
        """
        self._env = lmdb.open(str(path), map_size=max_size, max_dbs=categories)

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
        db_name = f"__db_{category}"
        return self._env.open_db(db_name.encode(), txn=txn, dupsort=False)

    def get(self, key: str, category: Optional[str] = None):
        """Получить данные из хранилища

        :param key:
            Ключ
        :param category:
            Необязательная категория
        :return:
            Значение
        """
        # Нужна трансакция на запись при получении значения из несуществующей категории - буде создана
        # база для этой категории
        with self._env.begin(write=True, buffers=True) as txn:
            db = self._category_db(category, txn)
            raw_value = txn.get(key.encode(), db=db)
        if raw_value is not None:
            return pickle.loads(raw_value)
        return None

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

            * psize - размер страницы базыSize of a database page in bytes.
            * depth - глубина B-деревьев.
            * branch_pages - количество внутренних страниц.
            * leaf_pages - количество листовых страниц.
            * overflow_pages - количество страниц с переполнением.
            * entries - количество сохраненных данных.

        """
        with self._env.begin() as txn:
            db = self._category_db(category, txn)
            return txn.stat(db)
