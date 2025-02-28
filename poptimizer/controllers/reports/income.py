import logging
from typing import Final

from poptimizer import errors
from poptimizer.adapters import mongo
from poptimizer.domain import cpi
from poptimizer.domain.funds import funds

_WEEK_IN_MONTH: Final = 365.25 / 7 / 12
_ROWS_PARAMS: Final = [
    (12, "1Y"),
    (1, "1M"),
    (1 / _WEEK_IN_MONTH, "1W"),
]


async def report(
    repo: mongo.Repo,
    investor: funds.Investor,
    months: int,
) -> None:
    lgr = logging.getLogger()

    fund = await repo.get(funds.Fund)
    cpi_table = await repo.get(cpi.CPI)

    if len(fund.rows) <= months or len(cpi_table.df) <= months:
        raise errors.DomainError("too many months")

    dividends = 0
    income = -fund.rows[-months - 1].get_value(investor)

    for lag in reversed(range(1, months + 1)):
        income *= cpi_table.df[-lag].cpi
        income -= fund.rows[-lag].inflows.get(investor, 0)

        dividends *= cpi_table.df[-lag].cpi
        dividends += fund.rows[-lag].get_dividends(investor)

    params = sorted([*_ROWS_PARAMS, (months, f"{months}M")], key=lambda x: x[0], reverse=True)
    income += fund.rows[-1].get_value(investor)
    income /= months
    dividends /= months

    label_align = len(str(months)) + 1
    max_factor = params[0][0]
    div_align = len(f"{round(max_factor * dividends, -3):_.0f}")
    income_align = len(f"{round(max_factor * income, -3):_.0f}")

    lgr.info("CPI-adjusted report for %s", investor)
    for factor, label in params:
        lgr.info(
            f"{label:<{label_align}}: Dividends = {round(dividends * factor, -3):>{div_align}_.0f} "
            f"/ Income = {round(income * factor, -3):>{income_align}_.0f}"
        )
