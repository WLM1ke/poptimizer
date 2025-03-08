import asyncio
import logging
from pathlib import Path
from typing import Final

from reportlab.pdfgen.canvas import Canvas

from poptimizer import consts
from poptimizer.adapters import mongo
from poptimizer.domain import domain
from poptimizer.domain.funds import funds
from poptimizer.domain.moex import quotes
from poptimizer.domain.portfolio import portfolio
from poptimizer.reports import risk
from poptimizer.reports.pdf import lower, middle, style, upper

_PATH: Final = consts.ROOT / "reports"
_REPORT_MONTHS: Final = 60

_FIRST_BLOCK_HEIGHT: Final = style.BLANK_HEIGHT * 0.76
_SECOND_BLOCK_HEIGHT: Final = style.BLANK_HEIGHT * 0.38
_THIRD_BLOCK_HEIGHT: Final = style.BLANK_HEIGHT * 0


async def _price_for_day(
    repo: mongo.Repo,
    pos: portfolio.Position,
    day: domain.Day,
) -> None:
    quote = await repo.get(quotes.Quotes, domain.UID(pos.ticker))
    for row in reversed(quote.df):
        if row.day <= day:
            pos.price = row.close

            return


async def _update_fund(
    repo: mongo.Repo,
    day: domain.Day,
    dividends: float,
    inflows: dict[funds.Investor, float],
) -> tuple[funds.Fund, portfolio.Portfolio]:
    async with asyncio.TaskGroup() as tg:
        port = await repo.get(portfolio.Portfolio)
        port.day = day

        for pos in port.positions:
            tg.create_task(_price_for_day(repo, pos, day))

        fund = await repo.get(funds.Fund)

    match len(fund.rows):
        case 0:
            fund.init(day=day, inflows=inflows)
        case _:
            fund.update(day=day, value=port.value, dividends=dividends, inflows=inflows)

    await repo.save(fund)

    return fund, port


def _make_report_files_path(day: domain.Day) -> tuple[Path, Path]:
    report_folder = _PATH / f"report {day}"
    if not report_folder.exists():
        report_folder.mkdir(parents=True)

    return report_folder / f"{day}.pdf", report_folder / f"{day}.json"


async def _make_report(
    repo: mongo.Repo,
    fund: funds.Fund,
    port: portfolio.Portfolio,
) -> Path:
    day = fund.day
    pdf_path, fund_path = _make_report_files_path(day)

    with fund_path.open("w") as json_file:
        json_file.write(fund.model_dump_json(indent=2))

    canvas = Canvas(pdf_path.open("wb"), pagesize=style.PAGE_SIZE)
    style.add_header(canvas, day)

    upper.add_block(
        canvas,
        style.BlockPosition(
            x=style.MARGIN,
            y=style.MARGIN + _FIRST_BLOCK_HEIGHT,
            width=style.BLANK_WIDTH,
            height=style.BLANK_HEIGHT - _FIRST_BLOCK_HEIGHT,
        ),
        fund,
    )
    style.add_block_delimiter(canvas, style.MARGIN + _FIRST_BLOCK_HEIGHT)

    middle.add_block(
        canvas,
        style.BlockPosition(
            x=style.MARGIN,
            y=style.MARGIN + _SECOND_BLOCK_HEIGHT,
            width=style.BLANK_WIDTH,
            height=_FIRST_BLOCK_HEIGHT - _SECOND_BLOCK_HEIGHT,
        ),
        await risk.prepare_cum_returns(repo, _REPORT_MONTHS),
    )
    style.add_block_delimiter(canvas, style.MARGIN + _SECOND_BLOCK_HEIGHT)

    lower.add_block(
        canvas,
        style.BlockPosition(
            x=style.MARGIN,
            y=style.MARGIN + _THIRD_BLOCK_HEIGHT,
            width=style.BLANK_WIDTH,
            height=_SECOND_BLOCK_HEIGHT - _THIRD_BLOCK_HEIGHT,
        ),
        port,
    )
    canvas.save()

    return pdf_path


async def report(
    repo: mongo.Repo,
    day: domain.Day,
    dividends: float,
    inflows: dict[funds.Investor, float],
) -> None:
    lgr = logging.getLogger()

    fund, port = await _update_fund(repo, day, dividends, inflows)
    lgr.info("Fund and Portfolio prices updated for %s", day)

    if len(fund.rows) <= _REPORT_MONTHS:
        lgr.info("Not enough data to make report - %d", len(fund.rows))

        return

    pdf_path = await _make_report(repo, fund, port)
    lgr.info("Report saved to %s", pdf_path.resolve())
