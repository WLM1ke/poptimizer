"""Загрузка данных по потребительской инфляции."""
import types

import aiohttp
import pandas as pd

from poptimizer import config
from poptimizer.data.adapters.gateways import gateways
from poptimizer.shared import adapters, col

# Параметры загрузки валидации данных
URL = "https://rosstat.gov.ru/storage/mediabank/i_ipc_1991-2021(1).xlsx"
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


async def _load_xlsx(session: aiohttp.ClientSession) -> pd.DataFrame:
    """Загрузка Excel-файла с данными по инфляции."""
    async with session.get(URL) as resp:
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

    async def __call__(self) -> pd.DataFrame:
        """Получение данных по  инфляции."""
        self._logger("Загрузка инфляции")

        df = await _load_xlsx(self._session)
        _validate(df)
        return _clean_up(df)
