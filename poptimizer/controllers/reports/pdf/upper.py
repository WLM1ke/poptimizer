from typing import Final

from reportlab import platypus
from reportlab.pdfgen.canvas import Canvas

from poptimizer.controllers.reports.pdf import style
from poptimizer.domain.funds import funds

_LEFT_PART_OF_BLOCK: Final = 2 / 3


def _prepare_flow_data(fund: funds.Fund) -> list[list[str]]:
    investors = sorted(fund.rows[-1].shares.keys())
    table_data = [["", *investors, "Portfolio"]]

    prev_row = fund.rows[-2]
    table_data.append(
        [
            f"{prev_row.day}",
            *[style.format_value(prev_row.get_value(investor)) for investor in investors],
            style.format_value(prev_row.value),
        ],
    )

    table_data.append(
        [
            "%",
            *[style.format_percent(prev_row.get_share(investor)) for investor in investors],
            style.format_percent(1),
        ],
    )

    last_row = fund.rows[-1]

    table_data.append(
        [
            "Pre Inflow",
            *[style.format_value(last_row.get_pre_inflow_value(investor)) for investor in investors],
            style.format_value(last_row.pre_inflow_value),
        ],
    )

    table_data.append(
        [
            "%",
            *[style.format_percent(last_row.get_pre_inflow_share(investor)) for investor in investors],
            style.format_percent(1),
        ],
    )

    table_data.append(
        [
            "Inflow",
            *[style.format_value(last_row.get_inflow(investor)) for investor in investors],
            style.format_value(last_row.inflow),
        ],
    )

    table_data.append(
        [
            f"{last_row.day}",
            *[style.format_value(last_row.get_value(investor)) for investor in investors],
            style.format_value(last_row.value),
        ],
    )

    table_data.append(
        [
            "%",
            *[style.format_percent(last_row.get_share(investor)) for investor in investors],
            style.format_percent(1),
        ],
    )

    return table_data


def _make_flow_table(fund: funds.Fund) -> platypus.Table:
    return platypus.Table(
        _prepare_flow_data(fund),
        style=(
            ("LINEBEFORE", (1, 0), (1, -1), style.LINE_WIDTH, style.LINE_COLOR),
            ("LINEBEFORE", (-1, 0), (-1, -1), style.LINE_WIDTH, style.LINE_COLOR),
            ("LINEABOVE", (0, 1), (-1, 1), style.LINE_WIDTH, style.LINE_COLOR),
            ("LINEABOVE", (0, 3), (-1, 3), style.LINE_WIDTH, style.LINE_COLOR),
            ("LINEABOVE", (0, 5), (-1, 6), style.LINE_WIDTH, style.LINE_COLOR),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (-1, 0), "CENTRE"),
            ("ALIGN", (0, 2), (0, 2), "CENTRE"),
            ("ALIGN", (0, 4), (0, 4), "CENTRE"),
            ("ALIGN", (0, -1), (0, -1), "CENTRE"),
        ),
        hAlign="LEFT",
    )


def _add_flow_block(
    canvas: Canvas,
    block_position: style.BlockPosition,
    fund: funds.Fund,
) -> None:
    left_block_header = platypus.Paragraph("Last Month Change and Inflow", style.BLOCK_HEADER_STYLE)
    left_table = _make_flow_table(fund)
    left_frame = platypus.Frame(
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
    left_frame.addFromList([left_block_header, left_table], canvas)


def _prepare_dividends_data(fund: funds.Fund) -> list[list[str]]:
    table_data = [["Period", "Dividends"]]

    table_data.append(
        [f"{fund.rows[-2].day} - {fund.rows[-1].day}", style.format_value(fund.rows[-1].dividends)],
    )

    table_data.extend(
        [
            f"{fund.rows[-12 * year - 13].day} - {fund.rows[-12 * year - 1].day}",
            style.format_value(sum(fund.rows[-12 * year - 1 - month].dividends for month in range(12))),
        ]
        for year in range(5)
    )

    return table_data


def _make_dividends_table(fund: funds.Fund) -> platypus.Table:
    return platypus.Table(
        data=_prepare_dividends_data(fund),
        style=(
            ("LINEBEFORE", (1, 0), (1, -1), style.LINE_WIDTH, style.LINE_COLOR),
            ("LINEABOVE", (0, 1), (-1, 2), style.LINE_WIDTH, style.LINE_COLOR),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "CENTRE"),
        ),
        hAlign="LEFT",
    )


def _add_dividends_block(
    canvas: Canvas,
    block_position: style.BlockPosition,
    fund: funds.Fund,
) -> None:
    right_block_header = platypus.Paragraph("Portfolio Dividends", style.BLOCK_HEADER_STYLE)
    right_table = _make_dividends_table(fund)
    right_frame = platypus.Frame(
        block_position.x + block_position.width * _LEFT_PART_OF_BLOCK,
        block_position.y,
        block_position.width * (1 - _LEFT_PART_OF_BLOCK),
        block_position.height,
        leftPadding=0,
        bottomPadding=0,
        rightPadding=0,
        topPadding=6,
        showBoundary=0,
    )
    right_frame.addFromList([right_block_header, right_table], canvas)


def add_block(
    canvas: Canvas,
    block_position: style.BlockPosition,
    fund: funds.Fund,
) -> None:
    _add_flow_block(canvas, block_position, fund)
    _add_dividends_block(canvas, block_position, fund)
