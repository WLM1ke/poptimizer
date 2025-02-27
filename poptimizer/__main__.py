import typer

from poptimizer import consts
from poptimizer.cli import app, feat, income, portfolio, risk


def _main() -> None:
    cli = typer.Typer(
        pretty_exceptions_enable=False,
        no_args_is_help=True,
        help=f"POptimizer {consts.__version__} - portfolio optimizer for MOEX shares and ETFs.",
    )
    cli.command()(app.run)
    cli.command()(portfolio.export)
    cli.command()(feat.stats)
    cli.command()(income.income)
    cli.command()(risk.risk)
    cli()


if __name__ == "__main__":
    _main()
