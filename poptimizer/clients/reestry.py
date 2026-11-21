import logging
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Final

from poptimizer.clients import parsing
from poptimizer.core import domain, errors
from poptimizer.data.div import raw

_RE_DATE: Final = re.compile(r"\d{1,2}[.]\d{2}[.]\d{4}")
_RE_DIV: Final = re.compile(r"(\d.*)[\xA0\s]руб")
_DIV_TRANSLATE: Final = str.maketrans({",": ".", " ": ""})


def div_parser(lgr: logging.Logger, html_page: str, data_col: int, first_day: domain.Day) -> list[raw.Row]:
    rows = parsing.xpath_elements(html_page, "//*/table/tbody/tr")

    rows_iter = iter(rows)
    _validate_div_header(next(rows_iter), data_col)

    return list(_parse_rows(lgr, rows_iter, data_col, first_day))


def _parse_rows(
    lgr: logging.Logger,
    rows_iter: Iterable[parsing.Element],
    data_col: int,
    first_day: domain.Day,
) -> Iterable[raw.Row]:
    for row in rows_iter:
        if "ИТОГО" in (date_raw := parsing.element_text(row[0])):
            continue

        if "НЕ ВЫПЛАЧИВАТЬ" in (raw_row := parsing.element_text(row[data_col])):
            continue

        date_re = _RE_DATE.search(date_raw)
        if date_re is None:
            lgr.warning(f"Bad dividend row {raw_row}")

            continue

        day = datetime.strptime(date_re.group(0), "%d.%m.%Y").date()
        if day < first_day:
            break

        div_re = _RE_DIV.search(raw_row)
        if not div_re:
            lgr.warning(f"Bad dividend row {raw_row}")

            continue

        yield raw.Row(day=day, dividend=float(div_re[1].translate(_DIV_TRANSLATE)))


def _validate_div_header(row: parsing.Element, data_col: int) -> None:
    share_type: tuple[str, ...] = ("привилегированную",)
    if data_col == 1:
        share_type = ("обыкновенную", "ГДР")

    header = parsing.element_html(row[data_col])

    if not any(word in header for word in share_type):
        raise errors.AdapterError(f"wrong dividends table header {header}")
