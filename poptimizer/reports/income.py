import logging
from typing import Final

from poptimizer.core import errors
from poptimizer.data.cpi import cpi
from poptimizer.fsm import uow
from poptimizer.reports.funds import funds

_WEEK_IN_MONTH: Final = 365.25 / 7 / 12
_ROWS_PARAMS: Final = [
    (12, "1Y"),
    (1, "1M"),
    (1 / _WEEK_IN_MONTH, "1W"),
]


async def report(
    lgr: logging.Logger,
    repo: uow.UOW,
    investor: funds.Investor,
    months: int,
) -> None:
    deflator = await _deflator(repo, months)
    income = await _real_income(repo, investor, deflator)
    monthly_income, shortfall = _monthly_income_and_shortfall(income)

    params = sorted([*_ROWS_PARAMS, (months, f"{months}M")], key=lambda x: x[0], reverse=True)

    label_align = len(str(months)) + 1
    max_factor = params[0][0]
    income_align = len(f"{round(max_factor * monthly_income, -3):_.0f}")

    lgr.info("CPI-adjusted report for %s", investor)
    for factor, label in params:
        lgr.info(f"{label:<{label_align}}: {round(monthly_income * factor, -3):>{income_align}_.0f}")

    lgr.info(f"Real shortfall - {round(shortfall, -5):_.0f}")


async def _deflator(repo: uow.UOW, months: int) -> list[float]:
    cpi_table = await repo.get(cpi.CPI)

    if len(cpi_table.df) < months:
        raise errors.DomainError("too many months")

    deflator = [1.0]

    for i in range(1, months + 1):
        deflator.append(deflator[-1] * cpi_table.df[-i].cpi)

    return list(reversed(deflator))


async def _real_income(repo: uow.UOW, investor: funds.Investor, deflator: list[float]) -> list[float]:
    fund = await repo.get(funds.Fund)

    months = len(deflator) - 1

    if len(fund.rows) <= months:
        raise errors.DomainError("too many months")

    return [
        (fund.rows[-i].get_value(investor) - fund.rows[-i].get_inflow(investor)) * deflator[-i]
        - fund.rows[-i - 1].get_value(investor) * deflator[-i - 1]
        for i in range(months, 0, -1)
    ]


def _monthly_income_and_shortfall(income: list[float]) -> tuple[float, float]:
    monthly_income = sum(income) / len(income)

    shortfall_max = 0
    reserve = 0
    for inc in income:
        reserve += inc - monthly_income
        shortfall_max = max(shortfall_max, -reserve)

    return monthly_income, shortfall_max
