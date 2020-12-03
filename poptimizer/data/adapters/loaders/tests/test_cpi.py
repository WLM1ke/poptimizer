"""Тесты для загрузки инфляции."""
import pandas as pd
import pytest

from poptimizer.data.adapters.loaders import cpi
from poptimizer.data.ports import outer
from poptimizer.shared import col


@pytest.mark.asyncio
async def test_get_cpi_url(mocker):
    """Поиск url страницы с CPI."""
    fake_session = mocker.MagicMock()
    fake_re = mocker.patch.object(cpi.re, "search")

    await cpi._get_cpi_url(fake_session)

    fake_session.get.assert_called_once_with(cpi.START_URL)
    fake_re.assert_called_once()
    fake_re.return_value.group.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_cpi_url_raises(mocker):
    """Обработка отсутствия ссылки на страницу с CPI."""
    fake_session = mocker.MagicMock()
    mocker.patch.object(cpi.re, "search", return_value=None)

    with pytest.raises(outer.DataError):
        await cpi._get_cpi_url(fake_session)


@pytest.mark.asyncio
async def test_get_xlsx_url(mocker):
    """Поиск url с Excel-файлом на странице."""
    fake_session = mocker.MagicMock()
    fake_get_cpi_url = mocker.patch.object(cpi, "_get_cpi_url")
    fake_re = mocker.patch.object(cpi.re, "search")

    url = await cpi._get_xlsx_url(fake_session)

    fake_get_cpi_url.assert_called_once_with(fake_session)
    fake_session.get.assert_called_once_with(fake_get_cpi_url.return_value)

    fake_re.assert_called_once()
    assert fake_re.call_args[0][0] is cpi.FILE_PATTERN

    assert url is fake_re.return_value.group.return_value


@pytest.mark.asyncio
async def test_get_xlsx_url_raises(mocker):
    """Обработка отсутствия url с Excel-файлом на странице."""
    fake_session = mocker.MagicMock()
    mocker.patch.object(cpi, "_get_cpi_url")
    mocker.patch.object(cpi.re, "search", return_value=None)

    with pytest.raises(outer.DataError):
        await cpi._get_xlsx_url(fake_session)


@pytest.mark.asyncio
async def test_load_xlsx(mocker):
    """Парсинг Excel с необходимыми параметрами."""
    mocker.patch.object(cpi.resources, "get_aiohttp_session")
    mocker.patch.object(cpi, "_get_xlsx_url")
    fake_read_excel = mocker.patch.object(cpi.pd, "read_excel")

    await cpi._load_xlsx()

    fake_read_excel.assert_called_once()

    _, kwargs = fake_read_excel.call_args
    assert kwargs == cpi.PARSING_PARAMETERS


VALID_CASES = (
    (
        pd.DataFrame([1]),
        "Таблица должна содержать 12 строк с месяцами",
    ),
    (
        pd.DataFrame(list(range(12)), columns=[1992]),
        "Первый год должен быть 1991",
    ),
    (
        pd.DataFrame(
            list(range(12)),
            columns=[1991],
            index=list(range(12)),
        ),
        "Первый месяц должен быть январь",
    ),
    (
        pd.DataFrame(
            list(range(12)),
            columns=[1991],
            index=["январь", *range(11)],
        ),
        None,
    ),
)


@pytest.mark.parametrize("df, msg", VALID_CASES)
def test_validate(df, msg):
    """Варианты ошибок в валидации исходного DataFrame с сайта."""
    if msg:
        with pytest.raises(outer.DataError, match=msg):
            cpi._validate(df)
    else:
        cpi._validate(df)


def test_clean_up():
    """Обработка исходного DataFrame с сайта."""
    df = pd.DataFrame(
        [[100, 200], [300, 400]],
        columns=[1992, 1993],
    )

    df_clean = cpi._clean_up(df)

    assert df_clean.values.tolist() == [
        [1.0],
        [3.0],
        [2.0],
        [4.0],
    ]
    assert df_clean.columns == [col.CPI]
    assert df_clean.index[0] == pd.Timestamp("1992-01-31")
    assert df_clean.index[-1] == pd.Timestamp("1992-04-30")


NAMES_CASES = (
    outer.TableName(outer.CPI, "test"),
    outer.TableName(outer.QUOTES, outer.CPI),
)


@pytest.mark.parametrize("table_name", NAMES_CASES)
@pytest.mark.asyncio
async def test_loader_raise_on_wrong_name(table_name):
    """Не верное название таблицы."""
    with pytest.raises(outer.DataError, match="Некорректное имя таблицы для обновления"):
        loader = cpi.CPILoader()
        await loader.get(table_name)


@pytest.mark.asyncio
async def test_loader(mocker):
    """Основной вариант работы загрузчика."""
    fake_load_xlsx = mocker.patch.object(cpi, "_load_xlsx")
    fake_validate = mocker.patch.object(cpi, "_validate")
    fake_clean_up = mocker.patch.object(cpi, "_clean_up")

    loader = cpi.CPILoader()
    table_name = outer.TableName(outer.CPI, outer.CPI)

    assert await loader.get(table_name) is fake_clean_up.return_value

    fake_load_xlsx.assert_called_once_with()
    fake_validate.assert_called_once_with(fake_load_xlsx.return_value)
    fake_clean_up.assert_called_once_with(fake_load_xlsx.return_value)
