import logging
import math
from typing import Final, cast

import pandas as pd
from scipy import stats

from poptimizer.core import domain, errors
from poptimizer.data.moex import index
from poptimizer.reports.funds import funds
from poptimizer.runtime import uow

PORTFOLIO: Final = "PORTFOLIO"
MOEX: Final = "MCFTRR"
RF: Final = "RUGBITR1Y"
_WIDTH: Final = len(PORTFOLIO)


async def prepare_cum_returns(repo: uow.Repo, months: int) -> pd.DataFrame:
    fund = await repo.get(funds.Fund)
    index_table = await repo.get(index.Index, domain.UID(index.MCF2TRR))
    rf_table = await repo.get(index.Index, domain.UID(index.RUGBITR1Y))

    if len(fund.rows) <= months:
        raise errors.DomainError("too many months")

    cum_return = [(fund.rows[-months - 1].day, 1.0)]
    for lag in reversed(range(1, months + 1)):
        prev_row = fund.rows[-lag - 1]
        row = fund.rows[-lag]
        cum_return.append(
            (
                row.day,
                cum_return[-1][1] * row.pre_inflow_value / prev_row.value,
            ),
        )

    portfolio = pd.DataFrame(cum_return, columns=["day", PORTFOLIO]).set_index("day")

    market = (
        pd.DataFrame([row.model_dump() for row in index_table.df])
        .set_index("day")
        .reindex(portfolio.index, method="ffill")
    )
    market = market / market.iloc[0]

    rf = (
        pd.DataFrame([row.model_dump() for row in rf_table.df])
        .set_index("day")
        .reindex(portfolio.index, method="ffill")
    )
    rf = rf / rf.iloc[0]

    returns = pd.concat([portfolio, market, rf], axis=1, sort=True)
    returns.columns = [PORTFOLIO, MOEX, RF]

    if len(returns) != months + 1:
        raise errors.DomainError("indexes and fund dates mismatch")

    return returns


async def report(lgr: logging.Logger, repo: uow.Repo, months: int) -> None:
    returns = await prepare_cum_returns(repo, months)
    returns = returns.pct_change(fill_method=None).dropna()

    lgr.info("Risk-return analysis for %dM", months)
    lgr.info(f"{'':<{_WIDTH}} {PORTFOLIO:>{_WIDTH}} {MOEX:>{_WIDTH}} {RF:>{_WIDTH}}")

    mean = cast("pd.Series[float]", returns.mean()) * 12
    lgr.info(f"{'MEAN':<{_WIDTH}} {mean[PORTFOLIO]:>{_WIDTH}.2%} {mean[MOEX]:>{_WIDTH}.2%} {mean[RF]:>{_WIDTH}.2%}")

    std = cast("pd.Series[float]", returns.std()) * math.sqrt(12)
    lgr.info(f"{'STD':<{_WIDTH}} {std[PORTFOLIO]:>{_WIDTH}.2%} {std[MOEX]:>{_WIDTH}.2%} {std[RF]:>{_WIDTH}.2%}")

    returns = returns.sub(returns[RF], axis=0)

    mean = cast("pd.Series[float]", returns.mean()) * 12
    lgr.info(f"{'MEAN - RF':<{_WIDTH}} {mean[PORTFOLIO]:>{_WIDTH}.2%} {mean[MOEX]:>{_WIDTH}.2%}")

    std = cast("pd.Series[float]", returns.std()) * math.sqrt(12)
    lgr.info(f"{'STD':<{_WIDTH}} {std[PORTFOLIO]:>{_WIDTH}.2%} {std[MOEX]:>{_WIDTH}.2%}")
    lgr.info(
        f"{'SHARPE':<{_WIDTH}} {mean[PORTFOLIO] / std[PORTFOLIO]:>{_WIDTH}.2%} {mean[MOEX] / std[MOEX]:>{_WIDTH}.2%}",
    )

    result = stats.linregress(returns[MOEX], returns[PORTFOLIO])
    lgr.info(f"{'BETA':<{_WIDTH}} {result.slope:>{_WIDTH}.2f}")
    lgr.info(f"{'ALPHA':<{_WIDTH}} {result.intercept * 12:>{_WIDTH}.2%}")
