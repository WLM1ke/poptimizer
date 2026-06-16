import csv
import logging
import re
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import Final, TextIO

from poptimizer.core import domain

_STATUS_LOOK_BACK_DAYS: Final = 14
_STATUS_DATE_FMT: Final = "%m/%d/%Y %H:%M:%S"
_STATUS_RE_TICKER: Final = re.compile(r",\s([A-Z]|[A-Z]{4}|[A-Z]{4}P|[A-Z][0-9])\s\[")


def status_parser(lgr: logging.Logger, csv_file: TextIO) -> Iterable[tuple[domain.Ticker, domain.Day]]:
    reader = csv.reader(csv_file)
    next(reader)

    for ticker_raw, date_raw, *_ in reader:
        timestamp = datetime.strptime(date_raw, _STATUS_DATE_FMT)
        day = date(timestamp.year, timestamp.month, timestamp.day)

        if day < date.today() - timedelta(days=_STATUS_LOOK_BACK_DAYS):
            continue

        match _STATUS_RE_TICKER.search(ticker_raw):
            case None:
                lgr.warning("Invalid ticker - %s", ticker_raw)
            case match_re:
                yield domain.Ticker(match_re[1]), day
