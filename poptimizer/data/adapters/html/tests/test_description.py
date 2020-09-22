"""Тесты для описания колонок."""
from datetime import datetime

from poptimizer.data.adapters.html import description


def test_date_parser():
    """Парсер для дат."""
    assert description.date_parser("-") is None
    assert description.date_parser("30.11.2018 (рек.)") == datetime(2018, 11, 30)
    assert description.date_parser("19.07.2017") == datetime(2017, 7, 19)


def test_div_parser():
    """Парсер для дивидендов."""
    assert description.div_parser("30,4") == 30.4
    assert description.div_parser("66.8 (рек.)") == 66.8
    assert description.div_parser("78,9 (прогноз)") == 78.9
    assert description.div_parser("2 097") == 2097.0
    assert description.div_parser("-") is None
