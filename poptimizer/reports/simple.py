"""Расчет дивидендов и дохода начиная с определенной даты в пересчете на неделю, месяц и год."""
import pandas as pd

from poptimizer import data
from poptimizer.reports import pdf, pdf_middle


def get_investor_data(file_name: str, investor_name: str) -> pd.DataFrame:
    """Формирует DataFrame с вкладами, стоимостью активов и дивидендами инвестора."""
    df = pdf.read_data(file_name)
    value_column = "Value_" + investor_name
    investor_share = df[value_column] / df["Value"]
    df["Dividends"] = df["Dividends"] * investor_share
    df = df[[investor_name, value_column, "Dividends"]]
    df.columns = ["Inflow", "Value", "Dividends"]
    return df


def constant_prices_data(
    report_name: str, investor_name: str, months: int
) -> pd.DataFrame:
    """Переводит данные в постоянные цены."""
    df = get_investor_data(report_name, investor_name)
    df = df.iloc[-months - 1 :]
    cpi = data.monthly_cpi(df.index[-1])
    cpi = cpi[-len(df) :]
    cpi = cpi.cumprod()
    cpi = cpi.iloc[-1] / cpi
    return df.mul(cpi.values, axis="index")


def rescale_and_format(x: float, divider: float) -> str:
    """Текстовое представление данных.

    Умножает на множитель и форматирует с округлением до тысяч, разделением разрядов и
    выравниванием вправо."""
    return f"{round(x / divider, -3):,.0f}".replace(",", " ").rjust(9)


def income(report_name: str, investor_name: str, months: int):
    """Распечатывает дивиденды и доход с начальной даты в среднем за год, месяц и неделю.

    Данные пересчитываются в постоянные цена на основе CPI для сопоставимости на длительных
    промежутках времени.

    :param report_name:
        Наименование файла с отчетом, из которого берутся исторические данные.
    :param investor_name:
        Имя инвестора, для которого осуществляется расчет.
    :param months:
        Количество месяцев, за которые анализируется статистика.
    """
    df = constant_prices_data(report_name, investor_name, months)
    dividends = df["Dividends"].iloc[1:].sum()
    incomes = df["Value"].iloc[-1] - df["Value"].iloc[0] - df["Inflow"].iloc[1:].sum()
    months = len(df) - 1
    periods = dict(Y=months / 12, M=months, W=(months / 12) * 365.25 / 7)
    print(
        f"\n{investor_name} в среднем (с коррекцией на инфляцию) за {months} месяцев:"
    )
    for period, divider in periods.items():
        print(
            f"1{period}:",
            f"Дивиденды = {rescale_and_format(dividends, divider)},",
            f"Доход = {rescale_and_format(incomes, divider)}",
        )


def monthly_returns(report_name: str, months: int) -> pd.DataFrame:
    """Необходимое количество месяцев для анализа."""
    df = pdf_middle.portfolio_cum_return(pdf.read_data(report_name).iloc[-months - 1 :])
    df = pd.concat([df, pdf_middle.index_cum_return(df)], axis=1).pct_change().dropna()
    df.columns = ["Portfolio", "MOEX"]
    return df


def stats(report_name: str, months: int):
    """Отчет ос статистических свойствах портфеля в сравнении с рынком.

    :param report_name:
        Наименование файла с отчетом, из которого берутся исторические данные.

    :param months:
        Количество месяцев, за которые анализируется статистика.
    """
    df = monthly_returns(report_name, months)
    results = dict()
    results["MEAN"] = df.mean() * 12
    results["STD"] = df.std() * 12 ** 0.5

    results[""] = ["", ""]
    results["G_MEAN"] = df.add(1).product(axis=0) ** (12 / len(df)) - 1
    results["PROXI"] = results["MEAN"] - results["STD"] ** 2 / 2
    results["Sharpe"] = results["MEAN"] / results["STD"]

    results = pd.DataFrame(results).T
    print(f"\n{results}")


def history(report_name: str, investor_name: str, months: int):
    """Распечатывает историческую статистику за определенное число месяцев дял инвестора и портфеля.

    :param report_name:
        Наименование файла с отчетом, из которого берутся исторические данные.
    :param investor_name:
        Имя инвестора, для которого осуществляется расчет.
    :param months:
        Количество месяцев, за которые анализируется статистика.
    """
    income(report_name, investor_name, months)
    stats(report_name, months)
