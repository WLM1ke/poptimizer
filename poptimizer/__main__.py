"""Запуск основных операций с помощью CLI:

- эволюции
- оптимизация
- проверка статуса дивидендов
"""
import typer

from poptimizer import data_old
from poptimizer.data_old import dividends_status
from poptimizer.evolve import Evolution
from poptimizer.portfolio import load_from_yaml, Optimizer


def evolve():
    """Run evolution."""
    ev = Evolution()
    date = data_old.last_history_date()
    port = load_from_yaml(date)
    ev.evolve(port)


def dividends(ticker: str):
    """Get dividends status."""
    dividends_status(ticker)


def optimize(date: str = typer.Argument(..., help="YYYY-MM-DD")):
    """Optimize portfolio."""
    port = load_from_yaml(date)
    opt = Optimizer(port)
    print(opt.portfolio)
    print(opt.metrics)
    print(opt)
    data_old.smart_lab_status(tuple(port.index[:-2]))


if __name__ == "__main__":
    app = typer.Typer(help="Run poptimizer subcommands.", add_completion=False)

    app.command()(evolve)
    app.command()(dividends)
    app.command()(optimize)

    app(prog_name="poptimizer")
