"""Расчет дивидендов и дохода начиная с определенной даты в пересчете на неделю, месяц и год."""
import pandas as pd

from poptimizer import config, data

SHEET_NAME = "Data"


def read_data(file_name: str):
    """Читает исходные данные по стоимости портфеля из файла."""
    return pd.read_excel(
        config.REPORTS_PATH / f"{file_name}.xlsx",
        sheet_name=SHEET_NAME,
        header=0,
        index_col=0,
        converters={"Date": pd.to_datetime},
    )


def get_investor_data(file_name: str, investor_name: str):
    """Формирует DataFrame с вкладами, стоимостью активов и дивидендами инвестора."""
    df = read_data(file_name)
    value_column = "Value_" + investor_name
    investor_share = df[value_column] / df["Value"]
    df["Dividends"] = df["Dividends"] * investor_share
    df = df[[investor_name, value_column, "Dividends"]]
    df.columns = ["Inflow", "Value", "Dividends"]
    return df


def constant_prices_data(
    report_name: str, investor_name: str, start_date: pd.Timestamp
):
    """Переводит данные в постоянные цены."""
    df = get_investor_data(report_name, investor_name)
    df = df.loc[start_date:]
    cpi = data.monthly_cpi(df.index[-1])
    cpi = cpi[-len(df) :]
    cpi = cpi.cumprod()
    cpi = cpi.iloc[-1] / cpi
    return df.mul(cpi.values, axis="index")


def rescale_and_format(x, divider):
    """Текстовое представление данных.

    Умножает на множитель и форматирует с округлением до тысяч, разделением разрядов и
    выравниванием вправо."""
    return f"{round(x / divider, -3):,.0f}".replace(",", " ").rjust(9)


def income(report_name: str, investor_name: str, start_date: pd.Timestamp):
    """Распечатывает дивиденды и доход с начальной даты в среднем за год, месяц и неделю.

    Данные пересчитываются в постоянные цена на основе CPI для сопоставимости на длительных
    промежутках времени.

    :param report_name:
        Наименование файла с отчетом, из которого берутся исторические данные.
    :param investor_name:
        Имя инвестора, для которого осуществляется расчет.
    :param start_date:
        Начальная дата, с которой анализируется статистика.
    """
    df = constant_prices_data(report_name, investor_name, start_date)
    dividends = df["Dividends"].iloc[1:].sum()
    income = df["Value"].iloc[-1] - df["Value"].iloc[0] - df["Inflow"].iloc[1:].sum()
    months = len(df) - 1
    periods = dict(Y=months / 12, M=months, W=(months / 12) * 365.25 / 7)
    print(
        f"\n{investor_name} с {start_date.date()} в среднем (с коррекцией на инфляцию):"
    )
    for period, divider in periods.items():
        print(
            f"1{period}:",
            f"Дивиденды = {rescale_and_format(dividends, divider)},",
            f"Доход = {rescale_and_format(income, divider)}",
        )
