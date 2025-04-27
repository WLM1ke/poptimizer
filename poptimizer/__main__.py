import typer

from poptimizer import consts
from poptimizer.cli import app, income, pdf, risk, stats


def _main() -> None:
    cli = typer.Typer(
        pretty_exceptions_enable=False,
        no_args_is_help=True,
        help=f"POptimizer {consts.__version__} - portfolio optimizer for MOEX shares and ETFs.",
    )
    cli.command()(app.run)
    cli.command()(stats.stats)
    cli.command()(income.income)
    cli.command()(risk.risk)
    cli.command()(pdf.pdf)
    cli()


if __name__ == "__main__":
    _main()
