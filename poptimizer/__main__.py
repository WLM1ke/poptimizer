import typer

from poptimizer.cli import app, portfolio


def main() -> None:
    cli = typer.Typer(pretty_exceptions_enable=False)
    cli.command()(app.run)
    cli.command()(portfolio.export)
    cli()


if __name__ == "__main__":
    main()
