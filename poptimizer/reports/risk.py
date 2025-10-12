import logging
from typing import Final

import pandas as pd
from scipy import stats  # type: ignore[reportMissingTypeStubs]

from poptimizer import errors
from poptimizer.adapters import mongo
from poptimizer.domain.funds import funds
from poptimizer.domain.moex import index

PORTFOLIO: Final = "PORTFOLIO"
MOEX: Final = "MCFTRR"
RF: Final = "RUGBITR1Y"
_WIDTH: Final = len(PORTFOLIO)


async def prepare_cum_returns(repo: mongo.Repo, months: int) -> pd.DataFrame:
    fund = await repo.get(funds.Fund)
    index_table = await repo.get(index.Index, index.MCF2TRR)
    rf_table = await repo.get(index.Index, index.RUGBITR1Y)

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

    portfolio = pd.DataFrame(cum_return, columns=["day", PORTFOLIO]).set_index("day")  # type: ignore[reportUnknownMemberType]

    market = pd.DataFrame(index_table.model_dump()["df"]).set_index("day").reindex(portfolio.index, method="ffill")  # type: ignore[reportUnknownMemberType]
    market = market / market.iloc[0]

    rf = pd.DataFrame(rf_table.model_dump()["df"]).set_index("day").reindex(portfolio.index, method="ffill")  # type: ignore[reportUnknownMemberType]
    rf = rf / rf.iloc[0]

    returns = pd.concat([portfolio, market, rf], axis=1, sort=True)
    returns.columns = [PORTFOLIO, MOEX, RF]

    if len(returns) != months + 1:
        raise errors.DomainError("indexes and fund dates mismatch")

    return returns


async def report(repo: mongo.Repo, months: int) -> None:
    lgr = logging.getLogger()

    returns = await prepare_cum_returns(repo, months)
    returns = returns.pct_change(fill_method=None).dropna()  # type: ignore[reportUnknownMemberType]

    lgr.info("Risk-return analysis for %dM", months)
    lgr.info(f"{'':<{_WIDTH}} {PORTFOLIO:>{_WIDTH}} {MOEX:>{_WIDTH}} {RF:>{_WIDTH}}")

    mean = returns.mean() * 12  # type: ignore[reportUnknownMemberType]
    lgr.info(f"{'MEAN':<{_WIDTH}} {mean[PORTFOLIO]:>{_WIDTH}.2%} {mean[MOEX]:>{_WIDTH}.2%} {mean[RF]:>{_WIDTH}.2%}")

    std = returns.std() * 12**0.5  # type: ignore[reportUnknownMemberType]
    lgr.info(f"{'STD':<{_WIDTH}} {std[PORTFOLIO]:>{_WIDTH}.2%} {std[MOEX]:>{_WIDTH}.2%} {std[RF]:>{_WIDTH}.2%}")

    returns = returns.sub(returns[RF], axis=0)  # type: ignore[reportUnknownMemberType]

    mean = returns.mean() * 12  # type: ignore[reportUnknownMemberType]
    lgr.info(f"{'MEAN - RF':<{_WIDTH}} {mean[PORTFOLIO]:>{_WIDTH}.2%} {mean[MOEX]:>{_WIDTH}.2%}")

    std = returns.std() * 12**0.5  # type: ignore[reportUnknownMemberType]
    lgr.info(f"{'STD':<{_WIDTH}} {std[PORTFOLIO]:>{_WIDTH}.2%} {std[MOEX]:>{_WIDTH}.2%}")
    lgr.info(
        f"{'SHARPE':<{_WIDTH}} {mean[PORTFOLIO] / std[PORTFOLIO]:>{_WIDTH}.2%} {mean[MOEX] / std[MOEX]:>{_WIDTH}.2%}"
    )

    result = stats.linregress(returns[MOEX], returns[PORTFOLIO])  # type: ignore[reportUnknownMemberType]
    lgr.info(f"{'BETA':<{_WIDTH}} {result.slope:>{_WIDTH}.2f}")  # type: ignore[reportUnknownMemberType]
    lgr.info(f"{'ALPHA':<{_WIDTH}} {result.intercept * 12:>{_WIDTH}.2%}")  # type: ignore[reportUnknownMemberType]
