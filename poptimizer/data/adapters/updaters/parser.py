"""Парсеры для html-таблиц."""
import re
from datetime import datetime
from typing import Callable, List, NamedTuple, Optional, Tuple, Union

import bs4
import pandas as pd

from poptimizer.data import ports

DIV_PATTERN = r".*\d"
DATE_PATTERN = r"\d{2}\.\d{2}\.\d{4}"


ParserFunc = Callable[[str], Union[None, float, datetime]]


class ColDesc(NamedTuple):
    """Описание столбца с данными.

    Используется для выбора определенных столбцов из html-таблицы, проверки ожидаемых значений в
    заголовках и преобразования из строк в нужный формат.

    - num: номер столбца
    - raw_name: часть исходного наименования
    - name: целевое наименование столбца
    - parser_func: функция для парсинга значений
    """

    num: int
    raw_name: Tuple[str, ...]
    name: str
    parser_func: ParserFunc


def date_parser(date: str) -> Optional[datetime]:
    """Функция парсинга значений в столбце с датами закрытия реестра."""
    re_date = re.search(DATE_PATTERN, date)
    if re_date:
        date_string = re_date.group(0)
        return datetime.strptime(date_string, "%d.%m.%Y")  # noqa: WPS323
    return None


def div_parser(div: str) -> Optional[float]:
    """Функция парсинга значений в столбце с дивидендами."""
    re_div = re.search(DIV_PATTERN, div)
    if re_div:
        date_string = re_div.group(0)
        date_string = date_string.replace(",", ".")
        date_string = date_string.replace(" ", "")
        return float(date_string)
    return None


class HTMLTable:
    """Извлекает таблицу из html-страницы."""

    def __init__(self, html: str, table_num: int, cols_desc: List[ColDesc]) -> None:
        """Проверяет наличие таблицы на html-странице."""
        soup = bs4.BeautifulSoup(html, "lxml")
        try:
            table = soup.find_all("table")[table_num]
        except IndexError:
            raise ports.DataError(f"На странице нет таблицы {table_num}")
        self._table = f"html{table}/html"
        self._cols_desc = cols_desc

    def get_df(self) -> pd.DataFrame:
        """Получает таблицу из html-документа и форматирует ее в соответствии с описанием."""
        converters = {desc.num: desc.parser_func for desc in self._cols_desc}
        header_nums = self._get_header_nums()
        df, *_ = pd.read_html(self._table, header=header_nums, converters=converters)
        self._validate_header(df.columns)
        return self._get_selected_col(df)

    def _get_header_nums(self) -> List[int]:
        """Формирует список строк, содержащих заголовки."""
        raw_name = self._cols_desc[0].raw_name
        num_of_headers = len(raw_name)
        headers = list(range(num_of_headers))
        return headers

    def _validate_header(self, columns: pd.Index) -> None:
        """Проверяет, что заголовки соответствуют описанию."""
        for desc in self._cols_desc:
            header = columns[desc.num]
            if not isinstance(header, tuple):
                header = [header]
            raw_name = desc.raw_name
            if all(part in name for part, name in zip(raw_name, header)):
                continue
            raise ports.DataError(f"Неверный заголовок: {desc.raw_name} не входит в {header}")

    def _get_selected_col(self, df: pd.DataFrame) -> pd.DataFrame:
        """Выбирает столбцы в соответствии с описанием."""
        cols_desc = self._cols_desc
        selected_col = [desc.num for desc in cols_desc]
        df = df.iloc[:, selected_col]
        df.columns = [desc.name for desc in cols_desc]
        index_name = cols_desc[0].name
        return df.set_index(index_name)
