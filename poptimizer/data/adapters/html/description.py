"""Описание колонок для парсера html-таблиц."""
import re
from datetime import datetime
from typing import Callable, NamedTuple, Optional, Tuple, Union

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
    parser_func: Optional[ParserFunc]


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
        div_string = re_div.group(0)
        div_string = div_string.replace(",", ".")
        div_string = div_string.replace(" ", "")
        return float(div_string)
    return None
