import sys

from pydantic_settings import BaseSettings, CliApp, CliSubCommand

from poptimizer.cli import app, config, div, income, keychain, metrics, pdf, risk, stats, tinkoff


class App(
    BaseSettings,
    cli_prog_name="poptimizer",
    cli_parse_args=True,
    cli_enforce_required=True,
    cli_use_class_docs_for_groups=True,
):
    """POptimizer - portfolio optimizer for MOEX shares and ETFs."""

    keychain: CliSubCommand[keychain.Keychain]
    run: CliSubCommand[app.Run]
    stats: CliSubCommand[stats.Stats]
    metrics: CliSubCommand[metrics.Metrics]
    income: CliSubCommand[income.Income]
    risk: CliSubCommand[risk.Risk]
    pdf: CliSubCommand[pdf.PDF]
    div: CliSubCommand[div.Div]
    tinkoff: CliSubCommand[tinkoff.Tinkoff]

    def cli_cmd(self) -> None:
        CliApp.run_subcommand(self)


if __name__ == "__main__":
    config.migrate_cfg()
    CliApp.run(App, cli_args=sys.argv[1:] or ["-h"])
