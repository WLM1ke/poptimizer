from typing import Final

import aiohttp
from pydantic import BaseModel

from poptimizer.cli import config

_URL_BASE: Final = "https://invest-public-api.tbank.ru/rest/tinkoff.public.invest.api.contract.v1"
_GET_ACCOUNTS_URL: Final = f"{_URL_BASE}.UsersService/GetAccounts"
_GET_POSITIONS_URL: Final = f"{_URL_BASE}.OperationsService/GetPositions"

_ACTIVE_ACCOUNT: Final = "ACCOUNT_STATUS_OPEN"
_ACCOUNT_TYPES_DESC: Final = {"ACCOUNT_TYPE_TINKOFF", "ACCOUNT_TYPE_TINKOFF_IIS"}


class Account(BaseModel):
    id: str
    type: str
    name: str

    def is_active(self) -> bool:
        return self.type in _ACCOUNT_TYPES_DESC


class _AccountsResponse(BaseModel):
    accounts: list[Account]


class Client:
    def __init__(self, http_session: aiohttp.ClientSession, accounts: list[config.Account]) -> None:
        self._http_session = http_session
        self._accounts = accounts

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    async def get_accounts(self, token: str) -> list[Account]:
        async with self._http_session.post(
            _GET_ACCOUNTS_URL,
            headers=self._headers(token),
            json={"status": _ACTIVE_ACCOUNT},
        ) as resp:
            json = await resp.json()

        acc_resp = _AccountsResponse.model_validate(json)

        return [acc for acc in acc_resp.accounts if acc.is_active()]
