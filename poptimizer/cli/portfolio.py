import contextlib
import json
import logging
from pathlib import Path
from typing import Final

import uvloop

from poptimizer import config
from poptimizer.adapters import logger, mongo
from poptimizer.cli import safe
from poptimizer.domain.portfolio import portfolio

_RUR: Final = "RUR"
_POSITIONS: Final = "positions"
_DEFAULT_OUT: Final = Path("portfolio") / "total.json"


async def _export_portfolio(lgr: logging.Logger, repo: mongo.Repo, out: Path) -> None:
    port = await repo.get(portfolio.Portfolio)
    positions = {pos.ticker: shares for pos in port.positions if (shares := sum(pos.accounts.values()))}

    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w") as file:
        json.dump(
            {_RUR: sum(port.cash.values()), _POSITIONS: positions},
            file,
            indent=2,
        )

    lgr.info("Portfolio saved to %s", out.resolve())


async def _run(out: Path) -> None:
    cfg = config.Cfg()

    async with contextlib.AsyncExitStack() as stack:
        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))
        lgr = await stack.enter_async_context(logger.init())
        repo = mongo.Repo(mongo_db)

        await safe.run(lgr, _export_portfolio(lgr, repo, out))


def export(out: Path = _DEFAULT_OUT) -> None:
    """Export current portfolio to json."""
    uvloop.run(_run(out))
