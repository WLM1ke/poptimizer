from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Final, Literal

import aiohttp
from pydantic import BaseModel, BeforeValidator, ValidationError

from poptimizer import errors
from poptimizer.cli import config
from poptimizer.domain import domain

_URL_BASE: Final = "https://invest-public-api.tbank.ru/rest/tinkoff.public.invest.api.contract.v1"
_GET_ACCOUNTS_URL: Final = f"{_URL_BASE}.UsersService/GetAccounts"
_GET_POSITIONS_URL: Final = f"{_URL_BASE}.OperationsService/GetPositions"

_ACTIVE_ACCOUNT: Final = "ACCOUNT_STATUS_OPEN"
_ACCOUNT_TYPES_DESC: Final = {"ACCOUNT_TYPE_TINKOFF", "ACCOUNT_TYPE_TINKOFF_IIS"}


class Account(BaseModel):
    id: str
    type: str
    name: domain.AccName

    def is_active(self) -> bool:
        return self.type in _ACCOUNT_TYPES_DESC


class _AccountsResponse(BaseModel):
    accounts: list[Account]


def _str_to_int(v: str | int) -> int:
    if isinstance(v, str):
        return int(v)

    return v


type Int = Annotated[int, BeforeValidator(_str_to_int)]


class Money(BaseModel):
    currency: Literal["rub"]
    units: Int
    nano: int


class Position(BaseModel):
    ticker: str
    # Бумаг после блокировки под заявки на продажу
    balance: Int
    # Бумаг заблокировано под заявки на продажу
    blocked: Int


class Positions(BaseModel):
    # Денег после блокировки под заявки на покупку
    money: list[Money]
    # Денег заблокировано под заявки на покупку
    blocked: list[Money]
    securities: list[Position]


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

    async def get_positions(self, account_name: domain.AccName) -> Positions | None:
        account = self._accounts.get(account_name)
        if account is None:
            return None

        async with (
            _wrap_err("failed to get positions"),
            self._http_session.post(
                _GET_POSITIONS_URL,
                headers=self._headers(account.token),
                json={"accountId": account.id},
            ) as resp,
        ):
            json = await resp.json()

            return Positions.model_validate(json)
