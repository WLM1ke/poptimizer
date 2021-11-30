"""Запуск основных операций с помощью CLI."""
import typer

from poptimizer import config
from poptimizer.data.views import div_status
from poptimizer.evolve import Evolution
from poptimizer.portfolio import load_from_yaml, optimizer_hmean, optimizer_resample


def evolve() -> None:
    """Run evolution."""
    ev = Evolution()
    ev.evolve()


def dividends(ticker: str) -> None:
    """Get dividends status."""
    div_status.dividends_validation(ticker)


def optimize(date: str = typer.Argument(..., help="YYYY-MM-DD")) -> None:
    """Optimize portfolio."""
    port = load_from_yaml(date)
    opt_type = {
        "resample": optimizer_resample.Optimizer,
        "hmean": optimizer_hmean.Optimizer,
    }[config.OPTIMIZER]
    opt = opt_type(port)
    print(opt.portfolio)
    print(opt.metrics)
    print(opt)
    div_status.new_dividends(tuple(port.index[:-2]))


if __name__ == "__main__":
    app = typer.Typer(help="Run poptimizer subcommands.", add_completion=False)

    app.command()(evolve)
    app.command()(dividends)
    app.command()(optimize)

    app(prog_name="poptimizer")
