"""Тесты для парсеров значений в таблицах."""
from datetime import datetime

import pytest

from poptimizer.data.adapters.html import cell_parser


def test_date_parser():
    """Парсер для дат."""
    assert cell_parser.date_ru("-") is None
    assert cell_parser.date_ru("30.11.2018 (рек.)") == datetime(2018, 11, 30)
    assert cell_parser.date_ru("19.07.2017") == datetime(2017, 7, 19)
    assert cell_parser.date_ru("9.07.2017") == datetime(2017, 7, 9)


def test_date_parser_us():
    """Парсер для дат в американском формате."""
    assert cell_parser.date_us("-") is None
    assert cell_parser.date_us("07/10/2019") == datetime(2019, 7, 10)
    assert cell_parser.date_us("12/9/2020") == datetime(2020, 12, 9)
    assert cell_parser.date_us("6/10/2020") == datetime(2020, 6, 10)
    assert cell_parser.date_us("3/8/2017") == datetime(2017, 3, 8)


def test_div_parser():
    """Парсер для дивидендов."""
    assert cell_parser.div_ru("30,4") == pytest.approx(30.4)
    assert cell_parser.div_ru("66.8 (рек.)") == pytest.approx(66.8)
    assert cell_parser.div_ru("78,9 (прогноз)") == pytest.approx(78.9)
    assert cell_parser.div_ru("2 097") == pytest.approx(2097.0)
    assert cell_parser.div_ru("-") is None


def test_div_parser_us():
    """Парсер для дивидендов в долларах."""
    assert cell_parser.div_us("$0.51") == pytest.approx(0.51)
    assert cell_parser.div_us("-") is None


def test_div_parser_with_cur():
    """Преобразование наименования валюты."""
    assert cell_parser.div_with_cur("2 027,5  ₽") == "2027.5RUR"
    assert cell_parser.div_with_cur("2,1  $") == "2.1USD"
    assert cell_parser.div_with_cur("") is None
