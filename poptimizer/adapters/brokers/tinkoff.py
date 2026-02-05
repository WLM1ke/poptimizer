from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

import aiohttp
from pydantic import BaseModel, ValidationError

from poptimizer import errors
from poptimizer.cli import config
from poptimizer.domain import domain
from poptimizer.use_cases.portfolio import positions

_URL_BASE: Final = "https://invest-public-api.tbank.ru/rest/tinkoff.public.invest.api.contract.v1"
_GET_ACCOUNTS_URL: Final = f"{_URL_BASE}.UsersService/GetAccounts"
_GET_POSITIONS_URL: Final = f"{_URL_BASE}.OperationsService/GetPositions"

_ACTIVE_ACCOUNT: Final = "ACCOUNT_STATUS_OPEN"
_ACCOUNT_TYPES_DESC: Final = {"ACCOUNT_TYPE_TINKOFF", "ACCOUNT_TYPE_TINKOFF_IIS"}

_TINKOFF_ETF_SUFFIX: Final = "@"


class Account(BaseModel):
    id: str
    type: str
    name: domain.AccName

    def is_active(self) -> bool:
        return self.type in _ACCOUNT_TYPES_DESC


class _AccountsResponse(BaseModel):
    accounts: list[Account]


@asynccontextmanager
async def _wrap_err(msg: str) -> AsyncIterator[None]:
    try:
        yield
    except (TimeoutError, aiohttp.ClientError, ValidationError) as err:
        raise errors.ControllersError(msg) from err


class Client:
    def __init__(self, http_session: aiohttp.ClientSession, accounts: list[config.Account]) -> None:
        self._http_session = http_session
        self._accounts = {acc.name: acc for acc in accounts}

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    async def get_accounts(self, token: str) -> list[Account]:
        async with (
            _wrap_err("failed to get accounts"),
            self._http_session.post(
                _GET_ACCOUNTS_URL,
                headers=self._headers(token),
                json={"status": _ACTIVE_ACCOUNT},
            ) as resp,
        ):
            json = await resp.json()

            acc_resp = _AccountsResponse.model_validate(json)

            return [acc for acc in acc_resp.accounts if acc.is_active()]

    def updatable_accounts(self) -> set[domain.AccName]:
        return set(self._accounts)

    async def get_positions(self, account_name: domain.AccName) -> positions.Positions:
        account = self._accounts.get(account_name)
        if account is None:
            raise errors.ControllersError(f"Account {account_name} not found")

        async with (
            _wrap_err("failed to get positions"),
            self._http_session.post(
                _GET_POSITIONS_URL,
                headers=self._headers(account.token),
                json={"accountId": account.id},
            ) as resp,
        ):
            json = await resp.json()

            raw_positions = positions.Positions.model_validate(json)

            for sec in raw_positions.securities:
                sec.ticker = _normalize_tickers(sec.ticker)

            return raw_positions


def _normalize_tickers(tickers: domain.Ticker) -> domain.Ticker:
    return domain.Ticker(tickers.removesuffix(_TINKOFF_ETF_SUFFIX))
