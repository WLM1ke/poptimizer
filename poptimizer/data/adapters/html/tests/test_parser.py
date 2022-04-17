"""Тесты для парсера html-таблиц."""
import aiohttp
import pandas as pd
import pytest

from poptimizer.data.adapters.html import cell_parser, description, parser

BAD_URL = "https://www.dohod.ru/wrong"

DESC_SINGLE_HEADER = description.ColDesc(
    num=2,
    raw_name=("(руб.)",),
    name="YAKG",
    parser_func=cell_parser.div_ru,
)
DESC_MULTI_HEADER = description.ColDesc(
    num=1,
    raw_name=("G", "Размер"),
    name="VSMO",
    parser_func=cell_parser.div_ru,
)


@pytest.mark.asyncio
async def test_get_html(mocker):
    """Получение html-странички."""
    fake_session = mocker.MagicMock()

    html = await parser.get_html(BAD_URL, fake_session)

    fake_session.get.assert_called_once()

    context_mng = fake_session.get.return_value
    context_mng.__aenter__.assert_called_once()  # noqa: WPS609

    respond = context_mng.__aenter__.return_value  # noqa: WPS609
    respond.raise_for_status.assert_called_once_with()
    respond.text.assert_called_once_with()
    assert html is respond.text.return_value


@pytest.mark.asyncio
async def test_get_html_raise(mocker):
    """Сообщение об ошибке при некорректном URL."""
    fake_session = mocker.MagicMock()
    context_mng = fake_session.get.return_value
    respond = context_mng.__aenter__.return_value  # noqa: WPS609
    respond.raise_for_status = mocker.Mock(side_effect=aiohttp.ClientResponseError("", ""))

    with pytest.raises(description.ParserError, match=f"Данные {BAD_URL} не загружены"):
        await parser.get_html(BAD_URL, fake_session)


HTML = "<html><table> a </table><table> b </table></html>"


def test_get_table_from_html():
    """Извлечение нужной таблицы."""
    table1 = "<html><table> b </table></html>"
    assert parser._get_table_from_html(HTML, 1) == table1


def test_get_table_from_html_raises():
    """Исключение при отсутствии необходимой таблицы."""
    with pytest.raises(description.ParserError, match="На странице нет таблицы 2"):
        assert parser._get_table_from_html(HTML, 2)


def test_get_raw_df(mocker):
    """Вызов функции с корректными параметрами."""
    read_html = mocker.patch.object(parser.pd, "read_html", return_value=["test_df"])
    cols_desc = [DESC_SINGLE_HEADER]
    assert parser._get_raw_df("test_table", cols_desc) == "test_df"
    read_html.assert_called_once_with(
        "test_table",
        header=[0],
        converters={2: cell_parser.div_ru},
        thousands=" ",
        displayed_only=False,
    )


HEADER_CASES = (
    (
        pd.Index(["aв", "b", "в (руб.) по"]),
        [DESC_SINGLE_HEADER],
        False,
    ),
    (
        pd.Index(["aв", "bе", "в (руб. ) по"]),
        [DESC_SINGLE_HEADER],
        True,
    ),
    (
        pd.Index(
            [
                ("a", "нb"),
                ("G", "gg Размер d"),
            ],
        ),
        [DESC_MULTI_HEADER],
        False,
    ),
    (
        pd.Index(
            [
                ("a", "b"),
                ("G", "мер d"),
            ],
        ),
        [DESC_MULTI_HEADER],
        True,
    ),
)


@pytest.mark.parametrize("columns, cols_desc, raises", HEADER_CASES)
def test_validate_header(columns, cols_desc, raises):
    """Комбинация корректных/ошибочных заголовков в одну/несколько строк."""
    if raises:
        with pytest.raises(description.ParserError, match="Неверный заголовок:"):
            parser._validate_header(columns, cols_desc)
    else:
        parser._validate_header(columns, cols_desc)


def test_get_selected_col():
    """Выбор и переименовывание столбцов."""
    df = pd.DataFrame(
        [[1, 2, 3], [4, 5, 6]],
        index=[1, 2],
        columns=["3", "4", "5"],
    )
    desc1 = description.ColDesc(num=2, raw_name=("5",), name="66", parser_func=None)
    desc2 = description.ColDesc(num=1, raw_name=("3",), name="44", parser_func=None)
    df_rez = pd.DataFrame(
        [2, 5],
        index=pd.Index([3, 6], name="66"),
        columns=["44"],
    )
    pd.testing.assert_frame_equal(parser._get_selected_col(df, [desc1, desc2]), df_rez)


def test_get_df_from_html(mocker):
    """Тестирование последовательности вызовов."""
    fake_get_table_from_html = mocker.patch.object(parser, "_get_table_from_html")
    fake_get_raw_df = mocker.patch.object(parser, "_get_raw_df")
    fake_validate_header = mocker.patch.object(parser, "_validate_header")
    fake_get_selected_col = mocker.patch.object(parser, "_get_selected_col")

    df_rez = parser.get_df_from_html("test_html", 2, [DESC_SINGLE_HEADER])

    fake_get_table_from_html.assert_called_once_with("test_html", 2)
    fake_get_raw_df.assert_called_once_with(
        fake_get_table_from_html.return_value,
        [DESC_SINGLE_HEADER],
    )
    fake_validate_header.assert_called_once_with(
        fake_get_raw_df.return_value.columns,
        [DESC_SINGLE_HEADER],
    )
    fake_get_selected_col.assert_called_once_with(
        fake_get_raw_df.return_value,
        [DESC_SINGLE_HEADER],
    )
    assert df_rez is fake_get_selected_col.return_value


@pytest.mark.asyncio
async def test_get_df_from_url(mocker):
    """Тестирование последовательности вызовов."""
    fake_get_html = mocker.patch.object(parser, "get_html")
    fake_get_df_from_html = mocker.patch.object(parser, "get_df_from_html")

    df_rez = await parser.get_df_from_url("test_url", 3, [DESC_MULTI_HEADER])

    fake_get_html.assert_called_once_with("test_url")
    fake_get_df_from_html.assert_called_once_with(fake_get_html.return_value, 3, [DESC_MULTI_HEADER])
    assert df_rez is fake_get_df_from_html.return_value
