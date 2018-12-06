"""Абстрактный менеджер данных - предоставляет локальные данные и следит за их обновлением."""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Union, Optional

import numpy as np
import pandas as pd

from poptimizer import POptimizerError
from poptimizer.config import DATA_PATH
from poptimizer.storage import store, utils
from poptimizer.storage.store import MAX_SIZE, MAX_DBS


class AbstractDataManager(ABC):
    """Организует создание, обновление и предоставление локальных данных."""

    # Создавать данные с нуля не сопоставляя с имеющейся версией
    CREATE_FROM_SCRATCH = False
    # Требования к индексу у данных
    IS_UNIQUE = True
    IS_MONOTONIC = True

    def __init__(self, names: tuple, category: Optional[str]):
        """Для ускорения за счет асинхронного обновления данных можно передать кортеж с названиями
        необходимых данных.

        :param names:
            Наименования получаемых данных.
        :param category:
            Категория получаемых данных.
        """
        self._names = names
        self._category = category
        self._data = self.load()
        asyncio.run(self._check_update())

    @property
    def names(self):
        """Кортеж с наименованием данных"""
        return self._names

    @property
    def category(self):
        """Категория данных."""
        return self._category

    @property
    def data(self):
        """Словарь с обновленными по расписанию данными."""
        return self._data

    async def _check_update(self):
        """Запускает асинхронное обновление данных"""
        aws = []
        for name, value in self.data:
            if value is None:
                aws.append(self.create(name))
            else:
                if await self._need_update(name):
                    if self.CREATE_FROM_SCRATCH:
                        aws.append(self.create(name))
                    else:
                        aws.append(self.update(name))
        await asyncio.gather(*aws)

    def load(self):
        """Загрузка локальных данных без обновления."""
        with store.DataStore(DATA_PATH, MAX_SIZE, MAX_DBS) as db:
            return {name: db[name, self.category] for name in self.names}

    async def _need_update(self, name):
        """Проверка необходимости обновления данных"""
        return self.data[name].timestamp < await utils.update_timestamp()

    async def create(self, name: str):
        """Создает локальные данные с нуля или перезаписывает существующие.

        При необходимости индекс данных проверяется на уникальность и монотонность.

        :param name:
            Наименование данных.
        """
        logging.info(f"Создание локальных данных {self.category} -> {name}")
        df = await self._download_all(name)
        self._check_and_save_datum(name, df)

    def _check_and_save_datum(self, name, df):
        """Проверяет индекс данных, сохраняет их в локальное хранилище и данные класса."""
        self._validate_index(df)
        data = utils.Datum(df)
        self._put_in_store(name, data)
        self._data[name] = utils.Datum(df)

    def _validate_index(self, df):
        """Проверяет индекс данных с учетом настроек."""
        if self.IS_UNIQUE and not df.index.is_unique:
            raise POptimizerError(f"Индекс не уникальный")
        if self.IS_MONOTONIC and not df.index.is_monotonic_increasing:
            raise POptimizerError(f"Индекс не возрастает монотонно")

    def _put_in_store(self, name: str, data: utils.Datum):
        """Сохраняет данные в хранилище."""
        with store.DataStore(DATA_PATH, MAX_SIZE, MAX_DBS) as db:
            db[name, self.category] = data

    async def update(self, name: str):
        """Обновляет локальные данные.

        При отсутствии реализации функции частичной загрузки данных будет осуществлена их полная
        загрузка. Во время обновления проверяется совпадение новых данных с существующими,
        а индекс всех данных при необходимости проверяется на уникальность и монотонность.
        """
        logging.info(f"Обновление локальных данных {self.category} -> {name}")
        df_old = self.data[name].value
        try:
            df_new = await self._download_update(name)
        except NotImplementedError:
            df_new = await self._download_all(name)
        self._validate_new(name, df_old, df_new)
        old_elements = df_old.index.difference(df_new.index)
        df = df_old.loc[old_elements].append(df_new)
        self._check_and_save_datum(name, df)

    def _validate_new(
        self,
        name: str,
        df_old: Union[pd.DataFrame, pd.Series],
        df_new: Union[pd.DataFrame, pd.Series],
    ):
        """Проверяет соответствие старых и новых данных"""
        common_index = df_old.index.intersection(df_new.index)
        if isinstance(df_old, pd.Series):
            condition = np.allclose(df_old.loc[common_index], df_new.loc[common_index])
        else:
            df_old_not_object = df_old.select_dtypes(exclude="object").loc[common_index]
            df_new_not_object = df_new.select_dtypes(exclude="object").loc[common_index]
            condition_not_object = np.allclose(
                df_old_not_object, df_new_not_object, equal_nan=True
            )

            df_old_object = df_old.select_dtypes(include="object").loc[common_index]
            df_new_object = df_new.select_dtypes(include="object").loc[common_index]
            condition_object = df_old_object.equals(df_new_object)

            condition = condition_not_object and condition_object
        if not condition:
            raise POptimizerError(
                f"Ошибка обновления данных - существующие данные не соответствуют новым:\n"
                f"Категория - {self.category}\n"
                f"Название - {name}\n"
            )

    @abstractmethod
    async def _download_all(self, name: str):
        """Загружает все необходимые данные и при необходимости проводит их первичную обработку."""
        raise NotImplementedError

    @abstractmethod
    async def _download_update(self, name: str):
        """Загружает данные с последнего значения включительно в существующих данных.

        При отсутствии возможности частичной загрузки должна сохраняться реализация из абстрактного
        класса, а данные будут загружены полностью.
        """
        raise NotImplementedError
