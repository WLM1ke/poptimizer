"""Тесты для загрузки данных с сайта https://bcs-express.ru."""
from datetime import datetime

import bs4
import pandas as pd
import pytest

from poptimizer.data.adapters.gateways import bcs
from poptimizer.data.adapters.html import description, parser
from poptimizer.shared import col


@pytest.mark.asyncio
async def test_get_rows(mocker):
    """Запрос отправляется на корректный адрес."""
    fake_get_html = mocker.patch.object(parser, "get_html")
    fake_bs = mocker.patch.object(bcs.bs4, "BeautifulSoup").return_value

    assert await bcs._get_rows("TEST") is fake_bs.find.return_value.find_all.return_value
    fake_get_html.assert_called_once_with("https://bcs-express.ru/kotirovki-i-grafiki/TEST")


@pytest.mark.asyncio
async def test_get_rows_no_div_table(mocker):
    """Регрессионный тест на случай отсутствия таблицы."""
    mocker.patch.object(parser, "get_html")
    fake_bs = mocker.patch.object(bcs.bs4, "BeautifulSoup").return_value
    fake_bs.find.return_value = None

    rows = await bcs._get_rows("TEST")
    assert isinstance(rows, list)
    assert not rows


TEST_ROWS = (
    (
        """<div class="dividends-table__row _item">
        <div class="dividends-table__cell _title">Транснефть ап 2018</div>
        <div class="dividends-table__cell _last-day">17.07.2019</div>
        <div class="dividends-table__cell _close-date">20.07.2019</div>
        <div class="dividends-table__cell _value">10 705,95</div>
        <div class="dividends-table__cell _price">165200</div>
        <div class="dividends-table__cell _profit">6,48%</div>
        </div>""",
        datetime(2019, 7, 20),
        (10705.95, "RUR"),
    ),
    (
        """<div class="dividends-table__row _item">
        <div class="dividends-table__cell _title">Транснефть ап 2018</div>
        <div class="dividends-table__cell _last-day">17.07.2019</div>
        <div class="dividends-table__cell _close-date">20.07.2019 </div>
        <div class="dividends-table__cell _value">100</div>
        <div class="dividends-table__cell _price">165200</div>
        <div class="dividends-table__cell _profit">6,48%</div>
        </div>""",
        datetime(2019, 7, 20),
        (100.0, "RUR"),
    ),
    (
        """<div class="dividends-table__row _item">
        <div class="dividends-table__cell _title">Транснефть ап 2018</div>
        <div class="dividends-table__cell _last-day">17.07.2019</div>
        <div class="dividends-table__cell _close-date">20.06.2019</div>
        <div class="dividends-table__cell _value">200,0</div>
        <div class="dividends-table__cell _price">165200</div>
        <div class="dividends-table__cell _profit">6,48%</div>
        </div>""",
        datetime(2019, 6, 20),
        (200.0, "RUR"),
    ),
    (
        """<div class="dividends-table__row _item">
        div class="dividends-table__cell _title">Транснефть ап 2006</div>
        <div class="dividends-table__cell _last-day">—</div>
        <div class="dividends-table__cell _close-date">—</div>
        <div class="dividends-table__cell _value">0</div>
        <div class="dividends-table__cell _price">—</div>
        <div class="dividends-table__cell _profit">—</div>
        </div>""",
        None,
        (0, "RUR"),
    ),
    (
        """<div class="dividends-table__row _item">
        <div class="dividends-table__cell _title">Транснефть ап 2018</div>
        <div class="dividends-table__cell _last-day">17.07.2019</div>
        <div class="dividends-table__cell _close-date">20.06.2019</div>
        <div class="dividends-table__cell _value">$0,09</div>
        <div class="dividends-table__cell _price">165200</div>
        <div class="dividends-table__cell _profit">6,48%</div>
        </div>""",
        datetime(2019, 6, 20),
        (0.09, "USD"),
    ),
    (
        """<div class="dividends-table__row _item">
        <div class="dividends-table__cell _title">Транснефть ап 2018</div>
        <div class="dividends-table__cell _last-day">17.07.2019</div>
        <div class="dividends-table__cell _close-date">20.06.2019</div>
        <div class="dividends-table__cell _value"></div>
        <div class="dividends-table__cell _price">165200</div>
        <div class="dividends-table__cell _profit">6,48%</div>
        </div>""",
        datetime(2019, 6, 20),
        (None, None),
    ),
)


@pytest.mark.parametrize("row, date, _", TEST_ROWS)
def test_parse_date(row, date, _):
    """Парсинг дат и пропусков."""
    soup = bs4.BeautifulSoup(row)
    assert bcs._parse_date(soup) == date


@pytest.mark.parametrize("row, _, div", TEST_ROWS)
def test_parse_div(row, _, div):
    """Парсинг, больших чисел, пропусков и чисел с запятой."""
    soup = bs4.BeautifulSoup(row)
    assert bcs._parse_div(soup) == div


@pytest.mark.asyncio
async def test_bcs_empty(mocker):
    """Регрессионный тест для случая отсутствия данных на html-странице."""
    mocker.patch.object(bcs, "_get_rows", side_effect=description.ParserError)

    df = await bcs.BCSGateway().__call__("TEST")

    assert df is None
