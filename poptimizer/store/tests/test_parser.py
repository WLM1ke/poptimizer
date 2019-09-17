import pandas as pd
import pytest

from poptimizer.config import POptimizerError
from poptimizer.store import parser

HTML = """
        <table>
          <tbody>
          <tr>
            <td rowspan=2> 1,1</td>
            <td> 2.2</td>
            <td rowspan=2 colspan=2> 3</td>
            <td rowspan=3> 4 (рек)</td>
          </tr>
          <tr>
            <td> 5.55 (сов)</td>
          </tr>
          <tr>
            <td> 66,6 пред</td>
            <td colspan=3> 7</td>
          </tr>
          </tbody>
        </table>
        <table>
          <tr>
            <td rowspan=2>1,1</td>
            <td>2.2</td>
            <td rowspan=2 colspan=2>3</td>
            <td rowspan=3>4 (рек)</td>
          </tr>
          <tr>
            <td>5.55 (сов)</td>
          </tr>
          <tr>
            <td>66,6 пред</td>
            <td colspan=3>7</td>
          </tr>
        </table>
       """

RESULT0 = [
    [" 1,1", " 2.2", " 3", " 3", " 4 (рек)"],
    [" 1,1", " 5.55 (сов)", " 3", " 3", " 4 (рек)"],
    [" 66,6 пред", " 7", " 7", " 7", " 4 (рек)"],
]

RESULT1 = [
    ["1,1", "2.2", "3", "3", "4 (рек)"],
    ["1,1", "5.55 (сов)", "3", "3", "4 (рек)"],
    ["66,6 пред", "7", "7", "7", "4 (рек)"],
]

DF_DATA = [
    [1.1, 2.2, 3.0, 3.0, 4.0],
    [1.1, 5.55, 3.0, 3.0, 4.0],
    [66.6, 7.0, 7.0, 7.0, 4.0],
]


def test_date_parser():
    assert parser.date_parser("-") is None
    assert parser.date_parser("30.11.2018 (рек.)") == pd.Timestamp("2018-11-30")
    assert parser.date_parser("19.07.2017") == pd.Timestamp("2017-07-19")


def test_div_parser():
    assert parser.div_parser("2.23") == 2.23
    assert parser.div_parser("30,4") == 30.4
    assert parser.div_parser("4") == 4
    assert parser.div_parser("66.8 (рек.)") == 66.8
    assert parser.div_parser("78,9 (прогноз)") == 78.9
    assert parser.div_parser("2 097") == 2097.0
    assert parser.div_parser("-") is None


def test_parse_tbody():
    table = parser.HTMLTableParser(HTML, 0)
    assert table.parsed_table == RESULT0


def test_parse_no_tbody():
    table = parser.HTMLTableParser(HTML, 1)
    assert table.parsed_table == RESULT1


def test_no_table():
    with pytest.raises(POptimizerError) as error:
        parser.HTMLTableParser(HTML, 2)
        assert error.value == "На странице нет таблицы 2"


def test_fast_second_parse():
    table = parser.HTMLTableParser(HTML, 1)
    assert table.parsed_table == RESULT1
    assert table.parsed_table == RESULT1


def test_get_formatted_data():
    table = parser.HTMLTableParser(HTML, 1)
    columns = [parser.DataColumn(f"col_{i}", i, {}, lambda x: x) for i in range(5)]
    df = pd.DataFrame(RESULT1)
    df.columns = [f"col_{i}" for i in range(5)]
    rez = df.to_dict("records")
    assert rez == table.get_formatted_data(columns)


def test_get_formatted_data_with_parsed_data():
    table = parser.HTMLTableParser(HTML, 1)
    columns = [
        parser.DataColumn(f"col_{i}", i, {}, parser.div_parser) for i in range(5)
    ]
    df = pd.DataFrame(DF_DATA)
    df.columns = [f"col_{i}" for i in range(5)]
    rez = df.to_dict("records")
    assert rez == table.get_formatted_data(columns)


def test_get_formatted_data_drop():
    table = parser.HTMLTableParser(HTML, 1)
    columns = [
        parser.DataColumn(f"col_{i}", i, {}, parser.div_parser) for i in range(5)
    ]
    df = pd.DataFrame(DF_DATA[1:2])
    df.columns = [f"col_{i}" for i in range(5)]
    rez = df.to_dict("records")
    assert rez == table.get_formatted_data(columns, 1, 1)


def test_get_formatted_data_validate():
    table = parser.HTMLTableParser(HTML, 1)
    columns = [
        parser.DataColumn(f"col_{i}", i, {0: RESULT1[0][i]}, parser.div_parser)
        for i in range(5)
    ]
    df = pd.DataFrame(DF_DATA[1:])
    df.columns = [f"col_{i}" for i in range(5)]
    rez = df.to_dict("records")
    assert rez == table.get_formatted_data(columns, 1)


def test_get_formatted_data_fail_validate():
    table = parser.HTMLTableParser(HTML, 1)
    columns = [parser.DataColumn("col", 1, {0: "2.2", 1: "test"}, lambda x: x)]
    with pytest.raises(POptimizerError) as error:
        table.get_formatted_data(columns)
        assert error.value == 'Значение в таблице "5.55 (сов)" - должно быть "test"'
