"""Парсеры значений дат и дивидендов."""
import re
from datetime import datetime
from typing import Final, Optional

from poptimizer.shared import col

DIV_PATTERN: Final = r".*\d"
DIV_PATTERN_US: Final = r"\$(.*\d)"
DIV_PATTERN_WITH_CUR = r".*\d\s{1,2}[$₽]"
DATE_PATTERN: Final = r"\d{1,2}\.\d{2}\.\d{4}"
DATE_PATTERN_US: Final = r"\d{1,2}\/\d{1,2}\/\d{4}"


def date_ru(date: str) -> Optional[datetime]:
    """Функция парсинга значений в столбце с датами закрытия реестра."""
    re_date = re.search(DATE_PATTERN, date)
    if re_date:
        date_string = re_date.group(0)
        return datetime.strptime(date_string, "%d.%m.%Y")  # noqa: WPS323
    return None


def date_us(date: str) -> Optional[datetime]:
    """Парсинг даты в американском формате."""
    re_date = re.search(DATE_PATTERN_US, date)
    if re_date:
        date_string = re_date.group(0)
        return datetime.strptime(date_string, "%m/%d/%Y")  # noqa: WPS323
    return None


def div_ru(div: str) -> Optional[float]:
    """Функция парсинга значений в столбце с дивидендами."""
    re_div = re.search(DIV_PATTERN, div)
    if re_div:
        div_string = re_div.group(0)
        div_string = div_string.replace(",", ".")
        div_string = div_string.replace(" ", "")
        return float(div_string)
    return None


def div_us(div: str) -> Optional[float]:
    """Функция парсинга дивидендов в долларах."""
    re_div = re.search(DIV_PATTERN_US, div)
    if re_div:
        div_string = re_div.group(1)
        div_string = div_string.replace(",", ".")
        div_string = div_string.replace(" ", "")
        return float(div_string)
    return None


def div_with_cur(div: str) -> Optional[str]:
    """Функция парсинга дивидендов с валютой в конце."""
    re_div = re.search(DIV_PATTERN_WITH_CUR, div)
    if re_div:
        div_string = re_div.group(0)
        div_string = div_string.replace(",", ".")
        div_string = div_string.replace(" ", "")
        div_string = div_string.replace("₽", col.RUR)
        return div_string.replace("$", col.USD)
    return None
