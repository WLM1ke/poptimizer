"""Загрузка данных по потребительской инфляции."""
import re
import types

import aiohttp
import pandas as pd

from poptimizer import config
from poptimizer.data.adapters.gateways import gateways
from poptimizer.shared import adapters, col

# Параметры загрузки валидации данных
START_URL = "https://rosstat.gov.ru/price"
URL_CORE = "https://rosstat.gov.ru/storage/mediabank/"
URL_END = "/Индексы%20потребительских%20цен%20.html"
CPI_PATTERN = re.compile("([a-zA-Z0-9]+)/Индексы")
FILE_PATTERN = re.compile("https://rosstat.gov.ru/storage/mediabank/[a-zA-Z0-9]+/i_ipc.xlsx")
END_OF_JAN = 31
PARSING_PARAMETERS = types.MappingProxyType(
    {
        "sheet_name": "ИПЦ",
        "header": 3,
        "skiprows": [4],
        "skipfooter": 3,
        "index_col": 0,
        "engine": "openpyxl",
    },
)
NUM_OF_MONTH = 12
FIRST_YEAR = 1991
FIRST_MONTH = "январь"


class CPIGatewayError(config.POptimizerError):
    """Ошибки, связанные с загрузкой данных по инфляции."""


async def _get_cpi_url(session: aiohttp.ClientSession) -> str:
    """Получить url на страницу с потребительской инфляцией."""
    async with session.get(START_URL) as resp:
        html = await resp.text()
    if match := re.search(CPI_PATTERN, html):
        url_code = match.group(1)
        return f"{URL_CORE}{url_code}{URL_END}"
    raise CPIGatewayError("На странице отсутствует ссылка на страницу с потребительской инфляцией")


async def _get_xlsx_url(session: aiohttp.ClientSession) -> str:
    """Получить url для файла с инфляцией."""
    cpi_url = await _get_cpi_url(session)
    async with session.get(cpi_url) as resp:
        html = await resp.text()
    if match := re.search(FILE_PATTERN, html):
        return match.group(0)
    raise CPIGatewayError("На странице отсутствует URL файла с инфляцией")


async def _load_xlsx(session: aiohttp.ClientSession) -> pd.DataFrame:
    """Загрузка Excel-файла с данными по инфляции."""
    file_url = await _get_xlsx_url(session)
    async with session.get(file_url) as resp:
        xls_file = await resp.read()
    return pd.read_excel(
        xls_file,
        **PARSING_PARAMETERS,
    )


def _validate(df: pd.DataFrame) -> None:
    """Проверка заголовков таблицы."""
    months, _ = df.shape
    first_year = df.columns[0]
    first_month = df.index[0]
    if months != NUM_OF_MONTH:
        raise CPIGatewayError("Таблица должна содержать 12 строк с месяцами")
    if first_year != FIRST_YEAR:
        raise CPIGatewayError("Первый год должен быть 1991")
    if first_month != FIRST_MONTH:
        raise CPIGatewayError("Первый месяц должен быть январь")


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


class CPIGateway(gateways.BaseGateway):
    """Обновление данных инфляции с https://rosstat.gov.ru."""

    _logger = adapters.AsyncLogger()

    async def get(self) -> pd.DataFrame:
        """Получение данных по  инфляции."""
        self._logger("Загрузка инфляции")

        df = await _load_xlsx(self._session)
        _validate(df)
        return _clean_up(df)
