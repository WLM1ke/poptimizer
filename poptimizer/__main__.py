"""Основная точка входа для запуска приложения."""
import typer

from poptimizer.cmd import data


def main() -> None:
    app = typer.Typer()
    app.command()(data.run)
    app()


if __name__ == "__main__":
    main()
