from io import BytesIO
from typing import TYPE_CHECKING, Final

import matplotlib.pyplot as plt
from reportlab import platypus
from reportlab.lib.units import inch

from poptimizer.domain.portfolio import portfolio
from poptimizer.reports.pdf import style

if TYPE_CHECKING:
    from reportlab.pdfgen.canvas import Canvas

_MAX_POSITIONS: Final = 9
_LEFT_PART_OF_BLOCK = 1 / 3


def _prepare_positions_data(port: portfolio.Portfolio) -> list[tuple[str, float, float]]:
    value = port.value()

    values = sorted(
        ((str(pos.ticker), pos.price * sum(pos.accounts.values())) for pos in port.positions),
        key=lambda pos: pos[1],
        reverse=True,
    )[:_MAX_POSITIONS]
    values.append(("Other", value - sum(pos[1] for pos in values)))
    values.append(("Portfolio", value))

    return [(name, pos, pos / value) for name, pos in values]


def _make_portfolio_table(positions: list[tuple[str, float, float]]) -> platypus.Table:
    return platypus.Table(
        data=[
            ("", "Value", "Share"),
            *[(ticker, style.format_value(value), style.format_percent(share)) for ticker, value, share in positions],
        ],
        style=(
            ("LINEBEFORE", (1, 0), (1, -1), style.LINE_WIDTH, style.LINE_COLOR),
            ("LINEABOVE", (0, 1), (-1, 1), style.LINE_WIDTH, style.LINE_COLOR),
            ("LINEABOVE", (0, -1), (-1, -1), style.LINE_WIDTH, style.LINE_COLOR),
            ("ALIGN", (-2, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (-1, 0), "CENTRE"),
            ("FONTNAME", (0, -1), (-1, -1), style.BOLD_FONT),
        ),
        hAlign="LEFT",
    )


def _add_table_block(
    canvas: Canvas,
    block_position: style.BlockPosition,
    positions: list[tuple[str, float, float]],
) -> None:
    block_header = platypus.Paragraph("Portfolio Structure", style.BLOCK_HEADER_STYLE)
    table = _make_portfolio_table(positions)
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


def _make_plot(positions: list[tuple[str, float, float]], width: float, height: float) -> platypus.Image:
    share = [share for _, _, share in positions]
    labels = [f"{ticker} {style.format_percent(share)}" for ticker, _, share in positions]

    _, ax = plt.subplots(1, 1, figsize=(width / inch, height / inch))  # type: ignore[reportUnknownMemberType]
    _, texts = ax.pie(  # type: ignore[reportUnknownMemberType]
        share,
        labels=labels,
        startangle=90,
        counterclock=False,
        labeldistance=1.1,
    )
    plt.setp(texts, size=8)  # type: ignore[reportUnknownMemberType]
    ax.axis("equal")

    file = BytesIO()
    plt.savefig(file, dpi=300, format="png", transparent=True)  # type: ignore[reportUnknownMemberType]

    return platypus.Image(file, width, height)


def _add_plot_block(
    canvas: Canvas,
    block_position: style.BlockPosition,
    positions: list[tuple[str, float, float]],
) -> None:
    image = _make_plot(
        positions,
        block_position.width * (1 - _LEFT_PART_OF_BLOCK),
        block_position.height,
    )
    image.drawOn(
        canvas,
        block_position.x + block_position.width * _LEFT_PART_OF_BLOCK,
        block_position.y,
    )


def add_block(
    canvas: Canvas,
    block_position: style.BlockPosition,
    port: portfolio.Portfolio,
) -> None:
    positions = _prepare_positions_data(port)
    _add_table_block(canvas, block_position, positions)
    _add_plot_block(canvas, block_position, positions[:-1])
