"""Формирование блока pdf-файла с информацией о доходности портфеля."""
from io import BytesIO
from typing import Final

import matplotlib.pyplot as plt
import pandas as pd
from reportlab import platypus
from reportlab.lib.units import inch

from poptimizer.data.views import indexes
from poptimizer.reports.pdf_style import BLOCK_HEADER_STYLE, LINE_COLOR, LINE_WIDTH, BlockPosition
from poptimizer.reports.pdf_upper import get_investors_names

# Доля левой части блока - используется для таблицы
# В правой расположена диаграмма
_LEFT_PART_OF_BLOCK: Final = 1 / 3


def portfolio_cum_return(df: pd.DataFrame) -> pd.DataFrame:
    """Кумулятивная доходность портфеля."""
    names = get_investors_names(df)
    # После внесения средств
    post_value = df["Value"]
    # Перед внесением средств
    pre_value = post_value.subtract(df[names].sum(axis=1), fill_value=0)
    portfolio_return = pre_value / post_value.shift(1)
    portfolio_return.iloc[0] = 1

    return portfolio_return.cumprod()


def index_cum_return(df: pd.DataFrame) -> pd.DataFrame:
    """Кумулятивная доходность индекса привязанная к отчетным периодам."""
    date = df.index[-1]
    index = indexes.mcftrr(date)
    index = index.reindex(
        index=df.index,
        method="ffill",
    )

    return index / index.iloc[0]


def make_plot(df: pd.DataFrame, width: float, height: float) -> platypus.Image:
    """Строит график стоимости портфеля и возвращает объект pdf-изображения."""
    _, ax = plt.subplots(1, 1, figsize=(width / inch, height / inch))
    ax.spines["top"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter("{:.0f}%".format))
    plt.grid(True, "major", lw=0.5, c="black", alpha=0.3)
    plt.tick_params(bottom=False, top=False, left=False, right=False)

    portfolio = portfolio_cum_return(df) * 100 - 100
    total_return_index = index_cum_return(df) * 100 - 100
    plt.plot(portfolio.values)
    plt.plot(total_return_index.values)
    x = total_return_index.index.astype(str).str.slice(stop=7)
    x_ticks_loc = range(0, len(x), 12)
    x_ticks_labels = x[x_ticks_loc]
    plt.yticks(fontsize=8)
    plt.xticks(x_ticks_loc, x_ticks_labels, fontsize=8)
    plt.legend(
        ("Portfolio", "MOEX Russia Net Total Return (Resident)"),
        fontsize=8,
        frameon=False,
    )

    file = BytesIO()
    plt.savefig(file, dpi=300, format="png", transparent=True)

    return platypus.Image(file, width, height)


def make_list_of_lists_table(df: pd.DataFrame) -> list[list[str]]:
    """Создает таблицу доходности портфеля и индекса в виде списка списков."""
    portfolio = portfolio_cum_return(df)
    portfolio_return = portfolio.iloc[-1] / portfolio * 100 - 100
    index = index_cum_return(df)
    index_return = index.iloc[-1] / index * 100 - 100
    list_of_lists = [["Period", "Portfolio", "MOEX"]]
    i = 1
    while i < len(df):
        if i == 1:
            name = "1M"
        else:
            year = i // 12
            name = f"{year}Y"
        portfolio = portfolio_return.iloc[-i - 1]
        index = index_return.iloc[-i - 1]
        list_of_lists.append([f"{name}", f"{portfolio: .1f}%", f"{index: .1f}%"])
        if i == 1:
            i = 12
        else:
            i += 12

    return list_of_lists


def make_pdf_table(df: pd.DataFrame) -> platypus.Table:
    """Формирует и форматирует pdf-таблицу доходности портфеля и индекса."""
    list_of_lists_table = make_list_of_lists_table(df)
    style = platypus.TableStyle(
        [
            ("LINEBEFORE", (1, 0), (1, -1), LINE_WIDTH, LINE_COLOR),
            ("LINEABOVE", (0, 1), (-1, 2), LINE_WIDTH, LINE_COLOR),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (-1, 0), "CENTRE"),
        ]
    )
    table = platypus.Table(list_of_lists_table, style=style)
    table.hAlign = "LEFT"

    return table


def portfolio_return_block(df: pd.DataFrame, block_position: BlockPosition) -> None:
    """Формирует блок pdf-файла с информацией доходности портфеля и индекса.

    В левой части располагается табличка, а в правой части диаграмма.
    """
    block_header = platypus.Paragraph("Portfolio Return", BLOCK_HEADER_STYLE)
    table = make_pdf_table(df)
    frame = platypus.Frame(
        block_position.x,
        block_position.y,
        block_position.width * _LEFT_PART_OF_BLOCK,
        block_position.height,
        leftPadding=0,
        bottomPadding=0,
        rightPadding=0,
        topPadding=6,
        showBoundary=0,
    )
    frame.addFromList([block_header, table], block_position.canvas)
    image = make_plot(df, block_position.width * (1 - _LEFT_PART_OF_BLOCK), block_position.height)
    image.drawOn(
        block_position.canvas,
        block_position.x + block_position.width * _LEFT_PART_OF_BLOCK,
        block_position.y,
    )
