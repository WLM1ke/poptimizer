from typing import Final, Protocol

import aiohttp
from pydantic import BaseModel

_URL_BASE: Final = "https://invest-public-api.tbank.ru/rest/tinkoff.public.invest.api.contract.v1"
_GET_ACCOUNTS_URL: Final = f"{_URL_BASE}.UsersService/GetAccounts"
_GET_POSITIONS_URL: Final = f"{_URL_BASE}.OperationsService/GetPositions"

_ACTIVE_ACCOUNT: Final = "ACCOUNT_STATUS_OPEN"
_ACCOUNT_TYPES_DESC: Final = {"ACCOUNT_TYPE_TINKOFF", "ACCOUNT_TYPE_TINKOFF_IIS"}


class Account(Protocol):
    name: str
    id: str


class Agreement(Protocol):
    token: str
    accounts: list[Account]


class _Account(BaseModel):
    id: str
    type: str
    name: str
    status: str

    def is_active(self) -> bool:
        return self.status == _ACTIVE_ACCOUNT and self.type in _ACCOUNT_TYPES_DESC


class _AccountsResponse(BaseModel):
    accounts: list[_Account]


class Client:
    def __init__(self, http_session: aiohttp.ClientSession, agreements: list[Agreement]) -> None:
        self._http_session = http_session
        self._agreements = agreements

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
            json={"status": "ACCOUNT_STATUS_UNSPECIFIED"},
        ) as resp:
            json = await resp.json()

        acc_resp = _AccountsResponse.model_validate(json)

        return [acc for acc in acc_resp.accounts if acc.is_active()]
