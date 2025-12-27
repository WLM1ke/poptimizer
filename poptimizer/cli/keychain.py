import contextlib

import keyring
from pydantic import BaseModel, Field
from pydantic_settings import CliApp, CliPositionalArg, CliSubCommand

from poptimizer.adapters import logger
from poptimizer.cli import config


class Save(BaseModel):
    """Save keychain secret."""

    key: CliPositionalArg[str] = Field(description="Secret name to set")
    value: CliPositionalArg[str] = Field(description="Secret value to set")

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            lgr = await stack.enter_async_context(logger.init())

            keyring.set_password(config.KEYCHAIN_APP, self.key, self.value)
            lgr.info(f'Keychain secret {self.key} saved - use "{config.KEYCHAIN_PREFIX}{self.key}" in cfg.yaml')


class Get(BaseModel):
    """Get keychain secret."""

    key: CliPositionalArg[str] = Field(description="Secret name to get")

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            lgr = await stack.enter_async_context(logger.init())

            secret = keyring.get_password(config.KEYCHAIN_APP, self.key)

            match secret:
                case None:
                    lgr.error(f"Keychain secret {self.key} not found")
                case _:
                    lgr.info(f"Keychain secret {self.key} is {secret}")


class Delete(BaseModel):
    """Delete keychain secret."""

    key: CliPositionalArg[str] = Field(description="Secret name to delete")

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            lgr = await stack.enter_async_context(logger.init())

            secret = keyring.get_password(config.KEYCHAIN_APP, self.key)

            match secret:
                case None:
                    lgr.error(f"Keychain secret {self.key} not found")
                case _:
                    keyring.delete_password(config.KEYCHAIN_APP, self.key)
                    lgr.info(f"Keychain secret {self.key} is deleted")


class Keychain(BaseModel):
    """Manage keychain secrets."""

    save: CliSubCommand[Save]
    get: CliSubCommand[Get]
    delete: CliSubCommand[Delete]

    async def cli_cmd(self) -> None:
        CliApp.run_subcommand(self)
