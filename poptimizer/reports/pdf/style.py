from typing import TYPE_CHECKING, Final

from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm

from poptimizer.domain import domain

if TYPE_CHECKING:
    from reportlab.pdfgen.canvas import Canvas

PAGE_SIZE: Final = A4
MARGIN: Final = cm
BLANK_WIDTH: Final = PAGE_SIZE[0] - 2 * MARGIN
BLANK_HEIGHT: Final = PAGE_SIZE[1] - 2 * MARGIN

BLOCK_HEADER_STYLE: Final = ParagraphStyle(
    "Block_Header",
    fontName="Helvetica-Bold",
    spaceAfter=10,
)
LINE_COLOR: Final = colors.black
LINE_WIDTH: Final = 0.5
BOLD_FONT: Final = "Helvetica-Bold"

PAGE_HEADER_FONT_SIZE = 14
PAGE_HEADER_COLOR = colors.darkblue


class BlockPosition(BaseModel):
    x: float
    y: float
    width: float
    height: float


def format_value(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def format_percent(value: float) -> str:
    return f"{value:.2%}"


def add_header(canvas: Canvas, day: domain.Day) -> None:
    canvas.setFont(BOLD_FONT, size=PAGE_HEADER_FONT_SIZE)
    canvas.setFillColor(PAGE_HEADER_COLOR)
    canvas.drawString(
        MARGIN,
        MARGIN * 1.1 + BLANK_HEIGHT,
        f"PORTFOLIO REPORT: {day}",
    )
    canvas.setStrokeColor(PAGE_HEADER_COLOR)
    canvas.line(
        MARGIN,
        MARGIN + BLANK_HEIGHT,
        MARGIN + BLANK_WIDTH,
        MARGIN + BLANK_HEIGHT,
    )


def add_block_delimiter(canvas: Canvas, height: float) -> None:
    canvas.setStrokeColor(LINE_COLOR)
    canvas.setLineWidth(LINE_WIDTH)
    canvas.line(MARGIN, height, MARGIN + BLANK_WIDTH, height)
