"""Тесты для загрузки данных с сайта https://bcs-express.ru."""
from datetime import datetime

import bs4
import pandas as pd
import pytest

from poptimizer.data.adapters.loaders import bcs
from poptimizer.data.ports import outer


@pytest.mark.asyncio
async def test_get_rows(mocker):
    """Запрос отправляется на корректный адрес."""
    fake_get_html = mocker.patch.object(bcs.parser, "get_html")
    fake_bs = mocker.patch.object(bcs.bs4, "BeautifulSoup").return_value

    assert await bcs._get_rows("TEST") is fake_bs.find.return_value.find_all.return_value
    fake_get_html.assert_called_once_with("https://bcs-express.ru/kotirovki-i-grafiki/TEST")


@pytest.mark.asyncio
async def test_get_rows_no_div_table(mocker):
    """Регрессионный тест на случай отсутствия таблицы."""
    mocker.patch.object(bcs.parser, "get_html")
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
        10705.95,
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
        100.0,
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
        200.0,
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
        0,
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
async def test_bcs(mocker):
    """Проверка, что данные группируются и сортируются в нужном порядке."""
    rows = [bs4.BeautifulSoup(row_data[0]) for row_data in TEST_ROWS]
    mocker.patch.object(bcs, "_get_rows", return_value=rows)

    table = outer.TableName(outer.BCS, "TEST")
    df = await bcs.BCS().get(table)

    index = pd.DatetimeIndex(["2019-06-20", "2019-07-20"])
    df_rez = pd.DataFrame([200.0, 10805.95], columns=["TEST"], index=index)

    pd.testing.assert_frame_equal(df, df_rez)


@pytest.mark.asyncio
async def test_bcs_empty(mocker):
    """Регрессионный тест для случая отсутствия данных на html-странице."""
    mocker.patch.object(bcs, "_get_rows", return_value=[])

    table = outer.TableName(outer.BCS, "TEST")
    df = await bcs.BCS().get(table)

    pd.testing.assert_frame_equal(df, pd.DataFrame(columns=["TEST"], dtype="float64"))


@pytest.mark.asyncio
async def test_bcs_raise():
    """Ошибка при попытке загрузки данных для неверной таблицы."""
    loader = bcs.BCS()
    table = outer.TableName(outer.CONOMY, "TEST")

    with pytest.raises(outer.DataError, match="Некорректное имя таблицы для обновления"):
        await loader.get(table)
