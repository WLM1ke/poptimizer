"""Загрузка данных по потребительской инфляции."""
import re

import aiohttp
import pandas as pd

from poptimizer.data.adapters import logger
from poptimizer.data.config import resources
from poptimizer.data.ports import col, outer

# Параметры загрузки валидации данных
URL_CORE = "https://rosstat.gov.ru/storage/mediabank/pcRcsWuc/"
URL_END = "Индексы%20потребительских%20цен%20по%20Российской%20Федерации.html"
FILE_PATTERN = re.compile("https://rosstat.gov.ru/storage/mediabank/[a-zA-Z0-9]+/i_ipc.xlsx")
END_OF_JAN = 31
PARSING_PARAMETERS = dict(sheet_name="ИПЦ", header=3, skiprows=[4], skipfooter=3, index_col=0)
NUM_OF_MONTH = 12
FIRST_YEAR = 1991
FIRST_MONTH = "январь"


async def _get_xlsx_url(session: aiohttp.ClientSession) -> str:
    """Получить url для файла с инфляцией."""
    async with session.get(URL_CORE + URL_END) as resp:
        html = await resp.text()
    if match := re.search(FILE_PATTERN, html):
        return match.group(0)
    raise outer.DataError("На странице отсутствует URL файла с инфляцией")


async def _load_xlsx() -> pd.DataFrame:
    """Загрузка Excel-файла с данными по инфляции."""
    session = resources.get_aiohttp_session()
    file_url = await _get_xlsx_url(session)
    async with session.get(file_url) as resp:
        xls_file = await resp.read()
    return pd.read_excel(xls_file, **PARSING_PARAMETERS)


def _validate(df: pd.DataFrame) -> None:
    """Проверка заголовков таблицы."""
    months, _ = df.shape
    first_year = df.columns[0]
    first_month = df.index[0]
    if months != NUM_OF_MONTH:
        raise outer.DataError("Таблица должна содержать 12 строк с месяцами")
    if first_year != FIRST_YEAR:
        raise outer.DataError("Первый год должен быть 1991")
    if first_month != FIRST_MONTH:
        raise outer.DataError("Первый месяц должен быть январь")


def _clean_up(df: pd.DataFrame) -> pd.DataFrame:
    """Форматирование данных."""
    df = df.transpose().stack()
    first_year = df.index[0][0]
    df.index = pd.date_range(
        name=col.DATE,
        freq="M",
        start=pd.Timestamp(year=first_year, month=1, day=END_OF_JAN),
        periods=len(df),
    )
    df = df.div(100)
    return df.to_frame(col.CPI)


class CPILoader(logger.LoggerMixin, outer.AbstractLoader):
    """Обновление данных инфляции с https://rosstat.gov.ru."""

    async def get(self, table_name: outer.TableName) -> pd.DataFrame:
        """Получение данных по  инфляции."""
        name = self._log_and_validate_group(table_name, outer.CPI)
        if name != outer.CPI:
            raise outer.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        df = await _load_xlsx()
        _validate(df)
        return _clean_up(df)
