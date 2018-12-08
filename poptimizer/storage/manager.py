"""Абстрактный менеджер данных - предоставляет локальные данные и следит за их обновлением."""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Union, Optional, Tuple

import numpy as np
import pandas as pd

from poptimizer import POptimizerError
from poptimizer.storage import utils


class AbstractManager(ABC):
    """Организует создание, обновление и предоставление локальных данных.

    Для работы должна быть открыта клиентская сессия.
    """

    ISS_SESSION = None
    STORE = None

    # Создавать данные с нуля не сопоставляя с имеющейся версией
    CREATE_FROM_SCRATCH = False
    # Требования к индексу у данных
    IS_UNIQUE = True
    IS_MONOTONIC = True

    def __init__(self, names: Union[str, Tuple[str]], category: Optional[str] = None):
        """Для ускорения за счет асинхронного обновления данных передается кортеж с названиями
        необходимых данных.

        :param names:
            Наименования получаемых данных.
        :param category:
            Категория получаемых данных.
        """
        if isinstance(names, str):
            self._names = (names,)
        else:
            self._names = names
        self._category = category
        self._last_history_date = None
        self._data = self._load()

    @property
    def names(self):
        """Кортеж с наименованием данных"""
        return self._names

    @property
    def category(self):
        """Категория данных."""
        return self._category

    def _load(self):
        """Загрузка локальных данных без обновления."""
        return {name: self.STORE[name, self.category] for name in self.names}

    async def get(self):
        """Запускает асинхронное обновление данных."""
        update_timestamp = await utils.update_timestamp(self.STORE)
        self._last_history_date = update_timestamp.strftime("%Y-%m-%d")
        aws = []
        for name, value in self._data.items():
            if value is None:
                aws.append(self.create(name))
            elif value.timestamp < update_timestamp:
                if self.CREATE_FROM_SCRATCH:
                    aws.append(self.create(name))
                else:
                    aws.append(self.update(name))
        await asyncio.gather(*aws)
        if len(self.names) == 1:
            return self._data[self.names[0]].value
        return [self._data[name].value for name in self.names]

    async def create(self, name: str):
        """Создает локальные данные с нуля или перезаписывает существующие.

        При необходимости индекс данных проверяется на уникальность и монотонность.
        :param name:
            Наименование данных.
        """
        logging.info(f"Создание локальных данных {self.category} -> {name}")
        self._data[name] = None
        df = await self._download(name)
        self._check_and_save(name, df)

    def _check_and_save(self, name, df):
        """Проверяет индекс данных, сохраняет их в локальное хранилище и данные класса."""
        self._validate_index(df)
        data = utils.Datum(df)
        self.STORE[name, self.category] = data
        logging.info(f"Данных обновлены {self.category} -> {name}")
        self._data[name] = data

    def _validate_index(self, df):
        """Проверяет индекс данных с учетом настроек."""
        if self.IS_UNIQUE and not df.index.is_unique:
            raise POptimizerError(f"Индекс не уникальный")
        if self.IS_MONOTONIC and not df.index.is_monotonic_increasing:
            raise POptimizerError(f"Индекс не возрастает монотонно")

    async def update(self, name: str):
        """Обновляет локальные данные.

        Во время обновления проверяется совпадение новых данных с существующими, а индекс всех данных при
        необходимости проверяется на уникальность и монотонность.
        """
        logging.info(f"Обновление локальных данных {self.category} -> {name}")
        df_old = self._data[name].value
        df_new = await self._download(name)
        self._validate_new(name, df_old, df_new)
        old_elements = df_old.index.difference(df_new.index)
        df = df_old.loc[old_elements].append(df_new)
        self._check_and_save(name, df)

    def _validate_new(
        self,
        name: str,
        df_old: Union[pd.DataFrame, pd.Series],
        df_new: Union[pd.DataFrame, pd.Series],
    ):
        """Проверяет соответствие старых и новых данных"""
        common_index = df_old.index.intersection(df_new.index)
        if not np.allclose(df_old.loc[common_index], df_new.loc[common_index]):
            raise POptimizerError(
                f"Существующие данные не соответствуют новым:\n"
                f"Категория - {self.category}\n"
                f"Название - {name}\n"
            )

    @abstractmethod
    async def _download(self, name: str):
        """Загружает необходимые данные до даты self._last_history_date.
        Если self._data[name] = None, то должны загружаться все данные. В остальных случаях для ускорения
        по возможности должна поддерживаться частичная загрузка с маленьким пересечением с уже
        загруженными данными для проверки их стыковки.
        """
