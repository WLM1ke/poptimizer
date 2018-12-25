"""Основные стили pdf-файла."""
from collections import namedtuple
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas

PAGE_SIZE = A4
MARGIN = cm

PAGE_HEADER_FONT_SIZE = 14
BOLD_FONT = "Helvetica-Bold"
PAGE_HEADER_COLOR = colors.darkblue

BLOCK_HEADER_STYLE = ParagraphStyle(
    "Block_Header", fontName="Helvetica-Bold", spaceAfter=10
)

LINE_COLOR = colors.black
LINE_WIDTH = 0.5


def make_blank_report(pdf_path: Path):
    """Формирует пустой pdf-отчет."""
    return Canvas(str(pdf_path), pagesize=PAGE_SIZE)


def left_margin():
    """Левое поле страницы."""
    return MARGIN


def blank_width():
    """Ширина свободного пространства на странице."""
    return PAGE_SIZE[0] - 2 * MARGIN


def bottom_margin():
    """Нижнее поле"""
    return MARGIN


def blank_height():
    """Высота свободного пространства на странице."""
    return PAGE_SIZE[1] - 2 * MARGIN


def make_header(canvas: Canvas, date):
    """Рисует верхний колонтитул страницы."""
    canvas.setFont(BOLD_FONT, size=PAGE_HEADER_FONT_SIZE)
    canvas.setFillColor(PAGE_HEADER_COLOR)
    canvas.drawString(
        left_margin(),
        bottom_margin() * 1.1 + blank_height(),
        f"PORTFOLIO REPORT: {date}",
    )
    canvas.setStrokeColor(PAGE_HEADER_COLOR)
    canvas.line(
        left_margin(),
        bottom_margin() + blank_height(),
        left_margin() + blank_width(),
        bottom_margin() + blank_height(),
    )


def make_section_delimiter(canvas: Canvas, height):
    """Рисует горизонтальную линию разделителя между отделами."""
    canvas.setStrokeColor(LINE_COLOR)
    canvas.setLineWidth(LINE_WIDTH)
    canvas.line(left_margin(), height, left_margin() + blank_width(), height)


BlockPosition = namedtuple("BlockPosition", "canvas x y width height")
