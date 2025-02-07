import typer

from poptimizer import consts
from poptimizer.cli import app, portfolio


def _main() -> None:
    cli = typer.Typer(
        pretty_exceptions_enable=False,
        no_args_is_help=True,
        help=f"POptimizer {consts.__version__}",
    )
    cli.command()(app.run)
    cli.command()(portfolio.export)
    cli()


if __name__ == "__main__":
    _main()
