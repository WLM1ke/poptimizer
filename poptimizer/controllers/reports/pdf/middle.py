import io
from typing import Final

import matplotlib.pyplot as plt
import pandas as pd
from reportlab import platypus
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas

from poptimizer.controllers.reports import risk
from poptimizer.controllers.reports.pdf import style

_LEFT_PART_OF_BLOCK: Final = 1 / 3
_DPI: Final = 300
_MONTH_IN_YEAR: Final = 12


def _prepare_returns_data(returns: pd.DataFrame) -> list[list[str]]:
    table_data = [["Period", "Portfolio", "MOEX", "RF"]]

    returns = returns.sort_index(ascending=False)  # type: ignore[reportUnknownMemberType]

    portfolio: pd.Series[float] = returns[risk.PORTFOLIO]
    portfolio = portfolio.iloc[0] / portfolio - 1

    market: pd.Series[float] = returns[risk.MOEX]
    market = market.iloc[0] / market - 1

    rf: pd.Series[float] = returns[risk.RF]
    rf = rf.iloc[0] / rf - 1

    table_data.append(
        [
            "1M",
            style.format_percent(portfolio.iloc[1]),
            style.format_percent(market.iloc[1]),
            style.format_percent(rf.iloc[1]),
        ],
    )

    table_data.extend(
        [
            [
                f"{year}Y",
                style.format_percent(portfolio.iloc[year * _MONTH_IN_YEAR]),
                style.format_percent(market.iloc[year * _MONTH_IN_YEAR]),
                style.format_percent(rf.iloc[year * _MONTH_IN_YEAR]),
            ]
            for year in range(1, 6)
        ]
    )

    return table_data


def _make_returns_table(returns: pd.DataFrame) -> platypus.Table:
    return platypus.Table(
        _prepare_returns_data(returns),
        style=(
            ("LINEBEFORE", (1, 0), (1, -1), style.LINE_WIDTH, style.LINE_COLOR),
            ("LINEABOVE", (0, 1), (-1, 2), style.LINE_WIDTH, style.LINE_COLOR),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (-1, 0), "CENTRE"),
        ),
        hAlign="LEFT",
    )


def _add_table_block(
    canvas: Canvas,
    block_position: style.BlockPosition,
    returns: pd.DataFrame,
) -> None:
    block_header = platypus.Paragraph("Portfolio Return", style.BLOCK_HEADER_STYLE)
    table = _make_returns_table(returns)
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
    frame.addFromList([block_header, table], canvas)


def _make_plot(
    returns: pd.DataFrame,
    width: float,
    height: float,
) -> platypus.Image:
    _, ax = plt.subplots(  # type: ignore[reportUnknownMemberType]
        1,
        1,
        figsize=(width / inch, height / inch),
    )
    ax.spines["top"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.yaxis.set_major_formatter("{x:.0f}%")
    plt.grid(visible=True, which="major", lw=0.5, c="black", alpha=0.3)  # type: ignore[reportUnknownMemberType]
    plt.tick_params(bottom=False, top=False, left=False, right=False)  # type: ignore[reportUnknownMemberType]

    returns = returns.sub(1).mul(100)  # type: ignore[reportUnknownMemberType]
    plt.plot(returns[risk.PORTFOLIO].to_numpy())  # type: ignore[reportUnknownMemberType]
    plt.plot(returns[risk.MOEX].to_numpy())  # type: ignore[reportUnknownMemberType]
    plt.plot(returns[risk.RF].to_numpy())  # type: ignore[reportUnknownMemberType]

    x_ticks_labels = returns.index.astype(str).str.slice(stop=7)  # type: ignore[reportUnknownMemberType]
    x_ticks_loc = range(0, len(x_ticks_labels), _MONTH_IN_YEAR)  # type: ignore[reportUnknownMemberType]
    x_ticks_labels = x_ticks_labels[x_ticks_loc]  # type: ignore[reportUnknownMemberType]

    plt.yticks(fontsize=8)  # type: ignore[reportUnknownMemberType]
    plt.xticks(x_ticks_loc, x_ticks_labels, fontsize=8)  # type: ignore[reportUnknownMemberType]
    plt.legend(  # type: ignore[reportUnknownMemberType]
        (
            "Portfolio",
            "MOEX Russia Net Total Return (Resident)",
            "Government Bond Index 1Y Total Return",
        ),
        fontsize=8,
        frameon=False,
    )

    chart = io.BytesIO()
    plt.savefig(chart, dpi=_DPI, format="png", transparent=True)  # type: ignore[reportUnknownMemberType]

    return platypus.Image(chart, width, height)


def _add_plot_block(
    canvas: Canvas,
    block_position: style.BlockPosition,
    returns: pd.DataFrame,
) -> None:
    image = _make_plot(returns, block_position.width * (1 - _LEFT_PART_OF_BLOCK), block_position.height)
    image.drawOn(
        canvas,
        block_position.x + block_position.width * _LEFT_PART_OF_BLOCK,
        block_position.y,
    )


def add_block(
    canvas: Canvas,
    block_position: style.BlockPosition,
    returns: pd.DataFrame,
) -> None:
    _add_table_block(canvas, block_position, returns)
    _add_plot_block(canvas, block_position, returns)
