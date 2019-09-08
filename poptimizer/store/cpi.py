"""Менеджер данных по потребительской инфляции."""
from typing import Any, Optional

import pandas as pd

from poptimizer.config import POptimizerError
from poptimizer.store.manager_new import AbstractManager
from poptimizer.store.utils_new import MISC, DB, DATE

# Наименование данных по инфляции
CPI = "CPI"

# Параметры загрузки валидации данных
URL_CPI = "http://www.gks.ru/free_doc/new_site/prices/potr/I_ipc.xlsx"
PARSING_PARAMETERS = dict(
    sheet_name="ИПЦ", header=3, skiprows=[4], skipfooter=3, index_col=0
)
NUM_OF_MONTH = 12
FIRST_YEAR = 1991
FIRST_MONTH = "январь"


class Macro(AbstractManager):
    """Месячные данные по потребительской инфляции.

    По умолчанию данные записываются в основную базу, но для целей тестированию может быть указана
    другая база.
    """

    def __init__(self, db=DB) -> None:
        super().__init__(db=db, collection=MISC, validate_last=False)

    def _download(self, item: str, last_index: Optional[Any]):
        """Загружает полностью данные по инфляции с сайта ФСГС."""
        if item != CPI:
            raise POptimizerError(
                f"Отсутствуют данные {self._collection.full_name}.{item}"
            )
        df = pd.read_excel(URL_CPI, **PARSING_PARAMETERS)
        self._validate(df)
        df = df.transpose().stack()
        first_year = df.index[0][0]
        df.index = pd.date_range(
            name=DATE,
            freq="M",
            start=pd.Timestamp(year=first_year, month=1, day=31),
            periods=len(df),
        )
        df.name = CPI
        # Данные должны быть не в процентах, а в долях
        df = df.div(100)
        return df.reset_index().to_dict("records")

    @staticmethod
    def _validate(df: pd.DataFrame):
        """Проверка заголовков таблицы"""
        months, _ = df.shape
        first_year = df.columns[0]
        first_month = df.index[0]
        if months != NUM_OF_MONTH:
            raise POptimizerError("Таблица должна содержать 12 строк с месяцами")
        if first_year != FIRST_YEAR:
            raise POptimizerError("Первый год должен быть 1991")
        if first_month != FIRST_MONTH:
            raise POptimizerError("Первый месяц должен быть январь")
