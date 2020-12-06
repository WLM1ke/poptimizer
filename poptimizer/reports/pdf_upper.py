"""Верхний блок pdf - движение по портфелю и история дивидендов."""

import pandas as pd
from reportlab import platypus

from poptimizer.reports.pdf_style import (
    LINE_WIDTH,
    LINE_COLOR,
    BlockPosition,
    BLOCK_HEADER_STYLE,
)

# Доля левой части блока - используется для таблицы движения средств
# В правой расположена таблица дивидендов
LEFT_PART_OF_BLOCK = 0.67


def get_last_values(df: pd.DataFrame):
    """Выбирает данные по стоимости портфеля за последние два периода.

    Для отдельных инвесторов и по портфелю в целом.
    """
    columns = df.columns
    columns_names = columns[columns.str.contains("Value")]
    df = df[columns_names].iloc[-2:]
    df.index = df.index.date.astype(str)
    df.columns = df.columns.str.replace("Value_", "")
    df.columns = df.columns.str.replace("Value", "Portfolio")
    return df


def get_investors_names(df: pd.DataFrame):
    """Получает имена инвесторов."""
    columns = df.columns
    names = columns[columns.str.contains("Value_")]
    return names.str.slice(6)


def get_inflows(df: pd.DataFrame):
    """Объем внесенных средств за последний период."""
    investors_names = get_investors_names(df)
    inflow = df[investors_names].iloc[-1].fillna(0)
    inflow["Portfolio"] = inflow.sum()
    return inflow


def add_shares(table: pd.DataFrame):
    """Добавляет к таблице долю инвесторов в портфеле."""
    share = table.div(table["Portfolio"], axis="index")
    share.index = ["%"] * len(share)
    return pd.concat([table, share])


def make_flow_df(df: pd.DataFrame):
    """Формирует данные для отчета."""
    table = get_last_values(df)
    inflow = get_inflows(df)
    pre_inflow_value = table["Portfolio"].iloc[-1] - inflow["Portfolio"]
    table.loc["Pre Inflow"] = table.iloc[-2] * pre_inflow_value / table["Portfolio"].iloc[-2]
    table = add_shares(table)
    table.loc["Inflow"] = inflow.values
    # Правильная последовательность строк и наименования
    table = table.iloc[[0, 3, 2, 5, 6, 1, 4]]
    return table


def make_list_of_lists_flow(df: pd.DataFrame):
    """Создает таблицу движения средств в виде списка списков."""
    flow_df = make_flow_df(df)
    list_of_lists = [[""] + list(flow_df.columns)]
    for row, name in enumerate(flow_df.index):
        row_list = [name]
        for column, _ in enumerate(flow_df.columns):
            value = flow_df.iat[row, column]
            if name == "%":
                value = f"{value:.2%}"
            else:
                value = f"{value:,.0f}".replace(",", " ")
            row_list.append(value)
        list_of_lists.append(row_list)
    return list_of_lists


def make_pdf_flow(df: pd.DataFrame):
    """Формирует и форматирует pdf таблицу движения средств."""
    data = make_list_of_lists_flow(df)
    style = platypus.TableStyle(
        [
            ("LINEBEFORE", (1, 0), (1, -1), LINE_WIDTH, LINE_COLOR),
            ("LINEBEFORE", (-1, 0), (-1, -1), LINE_WIDTH, LINE_COLOR),
            ("LINEABOVE", (0, 1), (-1, 1), LINE_WIDTH, LINE_COLOR),
            ("LINEABOVE", (0, 3), (-1, 3), LINE_WIDTH, LINE_COLOR),
            ("LINEABOVE", (0, 5), (-1, 6), LINE_WIDTH, LINE_COLOR),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (-1, 0), "CENTRE"),
            ("ALIGN", (0, 2), (0, 2), "CENTRE"),
            ("ALIGN", (0, 4), (0, 4), "CENTRE"),
            ("ALIGN", (0, -1), (0, -1), "CENTRE"),
        ]
    )
    table = platypus.Table(data, style=style)
    table.hAlign = "LEFT"
    return table


def make_12m_dividends_df(df: pd.DataFrame):
    """Скользящие дивиденды за последние 12 месяцев."""
    return df["Dividends"].fillna(0).rolling(12).sum()


def make_list_of_lists_dividends(df: pd.DataFrame):
    """Создает таблицу дивидендов в виде списка списков."""
    list_of_lists = [["Period", "Dividends"]]
    index = df.index
    period = f"{index[-2].date()} - {index[-1].date()}"
    value = df["Dividends"].fillna(0).iloc[-1]
    value = f"{value:,.0f}".replace(",", " ")
    list_of_lists.append([period, value])
    df = make_12m_dividends_df(df)
    index = df.index
    for i in range(5):
        period = f"{index[-12 * i - 13].date()} - {index[-12 * i - 1].date()}"
        value = df.iloc[-12 * i - 1]
        value = f"{value:,.0f}".replace(",", " ")
        list_of_lists.append([period, value])
    return list_of_lists


def make_pdf_dividends(df: pd.DataFrame):
    """Формирует и форматирует pdf таблицу с дивидендными выплатами"""
    data = make_list_of_lists_dividends(df)
    style = platypus.TableStyle(
        [
            ("LINEBEFORE", (1, 0), (1, -1), LINE_WIDTH, LINE_COLOR),
            ("LINEABOVE", (0, 1), (-1, 2), LINE_WIDTH, LINE_COLOR),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "CENTRE"),
        ]
    )
    table = platypus.Table(data=data, style=style)
    table.hAlign = "LEFT"
    return table


def flow_and_dividends_block(df: pd.DataFrame, block_position: BlockPosition):
    """Формирует блок pdf-файла с информацией движении средств и дивидендах.

    В левой части располагается табличка движения средств, а в правой - таблица дивидендов.
    """
    left_block_header = platypus.Paragraph("Last Month Change and Inflow", BLOCK_HEADER_STYLE)
    left_table = make_pdf_flow(df)
    left_frame = platypus.Frame(
        block_position.x,
        block_position.y,
        block_position.width * LEFT_PART_OF_BLOCK,
        block_position.height,
        leftPadding=0,
        bottomPadding=0,
        rightPadding=0,
        topPadding=6,
        showBoundary=0,
    )
    left_frame.addFromList([left_block_header, left_table], block_position.canvas)
    right_block_header = platypus.Paragraph("Portfolio Dividends", BLOCK_HEADER_STYLE)
    right_table = make_pdf_dividends(df)
    right_frame = platypus.Frame(
        block_position.x + block_position.width * LEFT_PART_OF_BLOCK,
        block_position.y,
        block_position.width * (1 - LEFT_PART_OF_BLOCK),
        block_position.height,
        leftPadding=0,
        bottomPadding=0,
        rightPadding=0,
        topPadding=6,
        showBoundary=0,
    )
    right_frame.addFromList([right_block_header, right_table], block_position.canvas)
