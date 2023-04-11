"""Загрузка данных по потребительской инфляции."""
import re
import types

import aiohttp
import pandas as pd

from poptimizer import config
from poptimizer.data.adapters.gateways import gateways
from poptimizer.shared import adapters, col

# Параметры загрузки валидации данных
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15",
}
_PRICES_PAGE = "https://rosstat.gov.ru/statistics/price"
_RE_FILE = re.compile(r"/[iI]pc[\-_]mes[\-_][0-9]{1,2}.xlsx")
_URL = "https://rosstat.gov.ru/storage/mediabank/{}"
END_OF_JAN = 31
PARSING_PARAMETERS = types.MappingProxyType(
    {
        "sheet_name": "01",
        "header": 3,
        "skiprows": [4],
        "skipfooter": 5,
        "index_col": 0,
        "engine": "openpyxl",
    },
)
NUM_OF_MONTH = 12
FIRST_YEAR = 1991
FIRST_MONTH = "январь"


class CPIGatewayError(config.POptimizerError):
    """Ошибки, связанные с загрузкой данных по инфляции."""


async def _load_prices_page(session: aiohttp.ClientSession, url: str = _PRICES_PAGE) -> str:
    async with session.get(url, headers=HEADERS) as resp:
        return await resp.text()


def _find_file_name(html: str) -> str:
    return _RE_FILE.search(html).group(0)


async def _load_and_parse_xlsx(session: aiohttp.ClientSession, file_name: str) -> pd.DataFrame:
    """Загрузка Excel-файла с данными по инфляции."""
    xls_file = await _load_xlsx(session, _URL.format(file_name))

    return pd.read_excel(
        xls_file,
        **PARSING_PARAMETERS,
    )


async def _load_xlsx(session: aiohttp.ClientSession, url: str) -> bytes:
    async with session.get(url, headers=HEADERS) as resp:
        return await resp.read()


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
        """Получение данных по инфляции."""
        self._logger("Загрузка инфляции")
        html = await _load_prices_page(self._session, _PRICES_PAGE)
        file_name = _find_file_name(html)

        df = await _load_and_parse_xlsx(self._session, file_name)
        _validate(df)

        return _clean_up(df)


if __name__ == '__main__':
    import asyncio

    loop = asyncio.get_event_loop()
    gw = CPIGateway()
    print(loop.run_until_complete(gw()))