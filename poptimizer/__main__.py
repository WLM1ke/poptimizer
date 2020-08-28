"""Запуск основных операций с помощью CLI:

- эволюции
- оптимизация
- проверка статуса дивидендов
"""
import typer

from poptimizer.data import views
from poptimizer.data_old import dividends_status
from poptimizer.evolve import Evolution
from poptimizer.portfolio import Optimizer, load_from_yaml


def evolve():
    """Run evolution."""
    ev = Evolution()
    date = views.last_history_date()
    port = load_from_yaml(date)
    ev.evolve(port)


def dividends(ticker: str):
    """Get dividends status."""
    views.dividends_validation(ticker)


def optimize(date: str = typer.Argument(..., help="YYYY-MM-DD")):
    """Optimize portfolio."""
    port = load_from_yaml(date)
    opt = Optimizer(port)
    print(opt.portfolio)
    print(opt.metrics)
    print(opt)
    views.new_on_smart_lab(tuple(port.index[:-2]))


if __name__ == "__main__":
    app = typer.Typer(help="Run poptimizer subcommands.", add_completion=False)

    app.command()(evolve)
    app.command()(dividends)
    app.command()(optimize)

    app(prog_name="poptimizer")
