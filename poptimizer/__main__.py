import typer

from poptimizer import app


def main() -> None:
    cli = typer.Typer()
    cli.command()(app.run)
    cli()


if __name__ == "__main__":
    main()
