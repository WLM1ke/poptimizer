"""Формирование блока pdf-файла с информацией о структуре портфеля."""
import types
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
from reportlab import platypus
from reportlab.lib.units import inch

from poptimizer.data.views import listing
from poptimizer.portfolio import CASH, PORTFOLIO, Portfolio
from poptimizer.reports.pdf_style import (
    BLOCK_HEADER_STYLE,
    BOLD_FONT,
    LINE_COLOR,
    LINE_WIDTH,
    BlockPosition,
)

# Количество строк в таблице, которое влезает в блок и нормально выглядит на диаграмме
MAX_TABLE_ROWS = 10

# Наименование типов бумаг
KINDS_MAPPING = types.MappingProxyType(
    {
        0: "Russian",
        1: "Russian",
        2: "Foreign",
        3: "ETF",
    }
)

# Доля левой части блока - используется для таблицы. В правой расположена диаграмма
LEFT_PART_OF_BLOCK = 1 / 3


def drop_small_positions(portfolio: Portfolio):
    """Отбрасывает нулевые позиции и при необходимости сокращает число строк до максимального.

    Объединяет самые мелкие позиции по типам бумаг.
    """
    value = portfolio.value
    portfolio_value = value[PORTFOLIO]
    value = value.iloc[:-2]
    value = value[value > 0]
    value = value.sort_values(ascending=False)
    value[CASH] = portfolio.value[CASH]

    kinds = listing.ticker_types().reindex(value.index)
    kinds[CASH] = 2
    kinds = kinds.replace(KINDS_MAPPING)

    n_types = len(set(kinds))
    max_rows = min(len(value), MAX_TABLE_ROWS - n_types)

    rez = value.iloc[:max_rows]
    other = pd.concat([value.iloc[max_rows:], kinds.iloc[max_rows:]], axis=1)
    rez = pd.concat(
        [
            rez,
            other.groupby("TICKER_TYPE").sum()["VALUE"].sort_values(),
        ],
        axis=0,
    )
    rez[PORTFOLIO] = portfolio_value

    return rez


def make_plot(portfolio: Portfolio, width: float, height: float):
    """Строит диаграмму структуры портфеля и возвращает объект pdf-изображения."""
    position_value = drop_small_positions(portfolio)
    position_share = position_value[:-1] / position_value[PORTFOLIO]
    labels = position_share.index + position_share.apply(lambda x: f"\n{x:.1%}")
    _, ax = plt.subplots(1, 1, figsize=(width / inch, height / inch))
    _, texts = ax.pie(
        position_share,
        labels=labels,
        startangle=90,
        counterclock=False,
        labeldistance=1.2,
    )
    plt.setp(texts, size=8)
    ax.axis("equal")
    file = BytesIO()
    plt.savefig(file, dpi=300, format="png", transparent=True)
    return platypus.Image(file, width, height)


def make_list_of_lists_table(portfolio: Portfolio):
    """Создает таблицу в виде списка списков."""
    position_value = drop_small_positions(portfolio)
    position_share = position_value / position_value[PORTFOLIO]
    list_of_lists = [["Name", "Value", "Share"]]
    for i in position_value.index:
        name = i
        value = f"{position_value[i]:,.0f}".replace(",", " ")
        share = f"{position_share[i]:.1%}"
        list_of_lists.append([name, value, share])
    return list_of_lists


def make_pdf_table(portfolio: Portfolio):
    """Создает и форматирует pdf-таблицу."""
    data = make_list_of_lists_table(portfolio)
    style = platypus.TableStyle(
        [
            ("LINEBEFORE", (1, 0), (1, -1), LINE_WIDTH, LINE_COLOR),
            ("LINEABOVE", (0, 1), (-1, 1), LINE_WIDTH, LINE_COLOR),
            ("LINEABOVE", (0, -1), (-1, -1), LINE_WIDTH, LINE_COLOR),
            ("ALIGN", (-2, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (-1, 0), "CENTRE"),
            ("FONTNAME", (0, -1), (-1, -1), BOLD_FONT),
        ]
    )
    table = platypus.Table(data=data, style=style)
    table.hAlign = "LEFT"
    return table


def portfolio_structure_block(portfolio: Portfolio, block_position: BlockPosition):
    """Формирует блок pdf-файла с информацией о структуре портфеля.

    В левой части располагается табличка структуры, а в правой части диаграмма.
    """
    block_header = platypus.Paragraph("Portfolio Structure", BLOCK_HEADER_STYLE)
    table = make_pdf_table(portfolio)
    frame = platypus.Frame(
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
    frame.addFromList([block_header, table], block_position.canvas)
    image = make_plot(
        portfolio,
        block_position.width * (1 - LEFT_PART_OF_BLOCK),
        block_position.height,
    )
    image.drawOn(
        block_position.canvas,
        block_position.x + block_position.width * LEFT_PART_OF_BLOCK,
        block_position.y,
    )
