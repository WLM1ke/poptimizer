"""Хранение истории стоимости портфеля и составление отчетов."""
import numpy as np
import pandas as pd

from poptimizer.config import REPORTS_PATH, POptimizerError
from poptimizer.portfolio import Portfolio, PORTFOLIO
from poptimizer.reports import pdf_style, pdf_upper, pdf_middle, pdf_lower

# Каталог с pdf-отчетами
PDF_PATH = REPORTS_PATH / "pdf"

# Лист с данными
SHEET_NAME = "Data"

# Положение блоков относительно нижнего поля
FIRST_BLOCK_HEIGHT = pdf_style.blank_height() * 0.76
SECOND_BLOCK_HEIGHT = pdf_style.blank_height() * 0.38
THIRD_BLOCK_HEIGHT = pdf_style.blank_height() * 0


def read_data(report_name: str):
    """Читает исходные данные по стоимости портфеля из файла."""
    data = pd.read_excel(
        REPORTS_PATH / f"{report_name}.xlsx",
        sheet_name=SHEET_NAME,
        header=0,
        index_col=0,
        converters={"Date": pd.to_datetime},
    )
    return data


def update_data(
    report_name: str, date: pd.Timestamp, value: float, inflows: dict, dividends: float
):
    """Обновляет файл с данными статистики изменения стоимости портфеля.

    Проверяет, что в этом месяце статистика еще не вносилась.

    :param report_name:
        Название файла с отчетом.
    :param date:
        Дата отчета.
    :param value:
        Стоимость активов.
    :param inflows:
        Словарь с именами инвесторов и внесенных ими средств за период.
    :param dividends:
        Дивиденды за период.
    """
    df = read_data(report_name)

    last_date = df.index[-1]
    if last_date + pd.DateOffset(months=1, day=1) > date:
        raise POptimizerError("В этом месяце данные уже вносились в отчет")

    total_inflow = 0
    for investor, inflow in inflows.items():
        if investor not in df.columns:
            raise POptimizerError(f"Неверное имя инвестора - {investor}")
        df.loc[date, investor] = inflow
        total_inflow += inflow

    df.loc[date, "Value"] = value

    portfolio_return = (value - total_inflow) / df.loc[last_date, "Value"]
    investors = pdf_upper.get_investors_names(df)
    value_labels = "Value_" + investors
    pre_inflow_value = df.loc[last_date, value_labels] * portfolio_return
    df.loc[date, value_labels] = pre_inflow_value.add(
        df.loc[date, investors].values, fill_value=0
    )

    if dividends == 0:
        df.loc[date, "Dividends"] = np.nan
    else:
        df.loc[date, "Dividends"] = dividends

    df.to_excel(REPORTS_PATH / f"{report_name}.xlsx", SHEET_NAME)


def make_report_files_path(report_name: str, date: pd.Timestamp):
    """Прокладывает путь и возвращает путь к файлу pdf-отчета и xlsx-отчета."""
    date = date.date()
    file_name = f"{report_name} {date}"
    report_folder = PDF_PATH / f"{file_name}"
    if not report_folder.exists():
        report_folder.mkdir(parents=True)
    return report_folder / f"{date}.pdf", report_folder / f"{date}.xlsx"


def make_report(report_name: str, portfolio: Portfolio):
    """Формирует отчет из pdf-файла и исходных xlsx-данных.

    Отчет сохраняется в PDF_PATH. Для каждого отчета создается папка с наименованием и датой, куда
    помещаются pdf- и xlsx-файлы.
    """
    data = read_data(report_name)
    # Верхний колонтитул
    date = portfolio.date
    pdf_path, xlsx_path = make_report_files_path(report_name, date)
    canvas = pdf_style.make_blank_report(pdf_path)
    pdf_style.make_header(canvas, date)
    # Верхний блок
    upper_block_position = pdf_style.BlockPosition(
        canvas=canvas,
        x=pdf_style.left_margin(),
        y=pdf_style.bottom_margin() + FIRST_BLOCK_HEIGHT,
        width=pdf_style.blank_width(),
        height=pdf_style.blank_height() - FIRST_BLOCK_HEIGHT,
    )
    pdf_upper.flow_and_dividends_block(data[-61:], upper_block_position)
    # Разделитель между верхним и средним блоком
    pdf_style.make_section_delimiter(
        canvas, pdf_style.bottom_margin() + FIRST_BLOCK_HEIGHT
    )
    # Средний блок
    middle_block_position = pdf_style.BlockPosition(
        canvas=canvas,
        x=pdf_style.left_margin(),
        y=pdf_style.bottom_margin() + SECOND_BLOCK_HEIGHT,
        width=pdf_style.blank_width(),
        height=FIRST_BLOCK_HEIGHT - SECOND_BLOCK_HEIGHT,
    )
    pdf_middle.portfolio_return_block(data[-61:], middle_block_position)
    # Разделитель между средним и нижним блоком
    pdf_style.make_section_delimiter(
        canvas, pdf_style.bottom_margin() + SECOND_BLOCK_HEIGHT
    )
    # Нижний блок
    lower_block_position = pdf_style.BlockPosition(
        canvas=canvas,
        x=pdf_style.left_margin(),
        y=pdf_style.bottom_margin() + THIRD_BLOCK_HEIGHT,
        width=pdf_style.blank_width(),
        height=SECOND_BLOCK_HEIGHT - THIRD_BLOCK_HEIGHT,
    )
    pdf_lower.portfolio_structure_block(portfolio, lower_block_position)
    # Сохранение pdf-отчета и xlsx-данных
    canvas.save()
    data.to_excel(xlsx_path, SHEET_NAME)


def report(report_name: str, portfolio: Portfolio, inflows: dict, dividends: float):
    """Обновляет данные статистики стоимости портфеля и создает отчет.

    Обновляется основной файл с отчетными данными. Создается его копия в каталоге с pdf-отчетом и
    формируется pdf-отчет.

    :param report_name:
        Наименование файла с отчетом.
    :param portfolio:
        Портфель на отчетную дату.
    :param inflows:
        Словарь с именами инвесторов и внесенных ими средств за период.
    :param dividends:
        Дивиденды за период.
    """
    update_data(
        report_name, portfolio.date, portfolio.value[PORTFOLIO], inflows, dividends
    )
    make_report(report_name, portfolio)
