"""Парсер html-таблиц."""
import re
from dataclasses import dataclass
from typing import Callable, List

import bs4
import pandas as pd

from poptimizer.config import POptimizerError

DIV_PATTERN = r".*\d"
DATE_PATTERN = r"\d{2}\.\d{2}\.\d{4}"


@dataclass(frozen=True)
class DataColumn:
    """Описание столбца с данными.

    Используется для выбора определенных столбцов из html-таблицы для построения DataFrame, проверки
    ожидаемых значений (обычно в заголовках и нижней части таблицы) и преобразования из строчных значений
    в нужный формат.
    """

    # Номер столбца
    index: int
    # Словарь с номером строки и ожидаемым значением для проверки - часть текста ячейки
    validation_dict: dict
    # Функция для преобразования текстового значения из html в нужный формат pd.DataFrame
    parser_func: Callable


def date_parser(data: str):
    """Функция парсинга значений в столбце с датами закрытия реестра."""
    result = re.search(DATE_PATTERN, data)
    if result:
        return pd.to_datetime(result.group(0), dayfirst=True)


def div_parser(data: str):
    """Функция парсинга значений в столбце с дивидендами."""
    result = re.search(DIV_PATTERN, data)
    if result:
        result = result.group(0)
        result = result.replace(",", ".")
        result = result.replace(" ", "")
        return float(result)


class HTMLTableParser:
    """Парсер html-таблиц.

    По номеру таблицы на странице формирует представление ее ячеек в виде списка списков. Ячейки с
    rowspan и colspan представляются в виде набора атомарных ячеек с одинаковыми значениями.
    """

    def __init__(self, html: str, table_index: int):
        soup = bs4.BeautifulSoup(html, "lxml")
        try:
            self._table = soup.find_all("table")[table_index]
        except IndexError:
            raise POptimizerError(f"На странице нет таблицы {table_index}")
        self._parsed_table = []

    @property
    def parsed_table(self):
        """html-таблица в виде списка списков ячеек."""
        if self._parsed_table:
            return self._parsed_table
        table = self._table
        row_pos = 0
        col_pos = 0
        for row in table.find_all("tr"):
            for cell in row.find_all(["th", "td"]):
                col_pos = self._find_empty_cell(row_pos, col_pos)
                row_span = int(cell.get("rowspan", 1))
                col_span = int(cell.get("colspan", 1))
                self._insert_cells(cell.text, row_pos, col_pos, row_span, col_span)
            row_pos += 1
            col_pos = 0
        return self._parsed_table

    def _find_empty_cell(self, row_pos, col_pos):
        """Ищет первую незаполненную ячейку в ряду и возвращает ее координату."""
        parse_table = self._parsed_table
        if row_pos >= len(parse_table):
            return col_pos
        row = parse_table[row_pos]
        while col_pos < len(row) and row[col_pos] is not None:
            col_pos += 1
        return col_pos

    def _insert_cells(self, value, row, col, row_span, col_span):
        """Заполняет таблицу значениями с учетом rowspan и colspan ячейки."""
        for row_pos in range(row, row + row_span):
            for col_pos in range(col, col + col_span):
                self._insert_cell(value, row_pos, col_pos)

    def _insert_cell(self, value, row_pos, col_pos):
        """Заполняет значение, при необходимости расширяя таблицу."""
        parse_table = self._parsed_table
        while row_pos >= len(parse_table):
            parse_table.append([None])
        row = parse_table[row_pos]
        while col_pos >= len(row):
            row.append(None)
        row[col_pos] = value

    def make_df(
        self, columns: List[DataColumn], drop_header: int = 0, drop_footer: int = 0
    ) -> pd.DataFrame:
        """Преобразует таблицу в DataFrame.

        Выбирает, проверяет и преобразует данные на основе описания колонок.

        :param columns:
            Список колонок, которые нужно проверить и оставить в DataFrame.
        :param drop_header:
            Сколько строк сверху нужно отбросить из таблицы при формировании DataFrame.
        :param drop_footer:
            Сколько строк снизу нужно отбросить из таблицы при формировании DataFrame.
        :return:
            Данные преобразованные в соответствии с описание.
        """
        self._validate_columns(columns)
        parsed_rows = self._yield_rows(columns, drop_header, drop_footer)
        return pd.DataFrame(parsed_rows)

    def _validate_columns(self, columns):
        """Проверка значений в колонках."""
        table = self.parsed_table
        for column in columns:
            for row, value in column.validation_dict.items():
                if value not in table[row][column.index]:
                    raise POptimizerError(
                        f"Значение в таблице {table[row][column.index]!r} - должно быть {value!r}"
                    )

    def _yield_rows(self, columns, drop_header, drop_footer):
        """Генерирует строки с избранными колонками со значениями после парсинга."""
        table = self._crop_table(drop_header, drop_footer)
        for row in table:
            yield [column.parser_func(row[column.index]) for column in columns]

    def _crop_table(self, drop_header, drop_footer):
        """Отбрасывает строки в начале и конце таблицы."""
        table = self.parsed_table
        drop_footer = len(table) - drop_footer
        table = table[drop_header:drop_footer]
        return table
