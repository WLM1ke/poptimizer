"""Основная точка входа для запуска приложения."""
import typer

from poptimizer import cmd


def main() -> None:
    app = typer.Typer(add_completion=False)
    app.command()(cmd.run)
    app()


if __name__ == "__main__":
    main()
