from typing import Final

import aiohttp
from pydantic import BaseModel, Field

from poptimizer.adapters.http import wrap_err
from poptimizer.cli import config
from poptimizer.core import domain, errors
from poptimizer.portfolio import actions

_URL_BASE: Final = "https://invest-public-api.tbank.ru/rest/tinkoff.public.invest.api.contract.v1"
_GET_ACCOUNTS_URL: Final = f"{_URL_BASE}.UsersService/GetAccounts"
_GET_POSITIONS_URL: Final = f"{_URL_BASE}.OperationsService/GetPositions"
_GET_ORDERS_URL: Final = f"{_URL_BASE}.OrdersService/GetOrders"

_ACTIVE_ACCOUNT: Final = "ACCOUNT_STATUS_OPEN"
_ACCOUNT_TYPES_DESC: Final = {"ACCOUNT_TYPE_TINKOFF", "ACCOUNT_TYPE_TINKOFF_IIS"}

_TINKOFF_ETF_SUFFIX: Final = "@"

_ACTIVE_ORDER_STATUSES: Final = [
    "EXECUTION_REPORT_STATUS_NEW",
    "EXECUTION_REPORT_STATUS_PARTIALLYFILL",
]


class Account(BaseModel):
    id: str
    type: str
    name: domain.AccName

    def is_active(self) -> bool:
        return self.type in _ACCOUNT_TYPES_DESC


class _AccountsResponse(BaseModel):
    accounts: list[Account]


class _OrderState(BaseModel):
    order_id: str = Field(alias="orderId")
    ticker: domain.Ticker
    status: str = Field(alias="executionReportStatus")


class _OrdersResponse(BaseModel):
    orders: list[_OrderState]


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
            wrap_err("failed to get accounts"),
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

    async def get_positions(self, account_name: domain.AccName) -> actions.Positions:
        account = self._accounts.get(account_name)
        if account is None:
            raise errors.ControllersError(f"Account {account_name} not found")

        async with (
            wrap_err("failed to get positions"),
            self._http_session.post(
                _GET_POSITIONS_URL,
                headers=self._headers(account.token),
                json={"accountId": account.id},
            ) as resp,
        ):
            json = await resp.json()

            raw_positions = actions.Positions.model_validate(json)

            for sec in raw_positions.securities:
                sec.ticker = _normalize_tickers(sec.ticker)

            return raw_positions

    async def get_orders(self, account_name: domain.AccName) -> list[domain.Ticker]:
        """Возвращает отсортированный список тикеров, по которым есть активные заявки."""
        account = self._accounts.get(account_name)
        if account is None:
            raise errors.ControllersError(f"Account {account_name} not found")

        async with (
            wrap_err("failed to get orders"),
            self._http_session.post(
                _GET_ORDERS_URL,
                headers=self._headers(account.token),
                json={"accountId": account.id},
            ) as resp,
        ):
            json = await resp.json()
            orders_response = _OrdersResponse.model_validate(json)

        return sorted(
            {
                _normalize_tickers(order.ticker)
                for order in orders_response.orders
                if order.status in _ACTIVE_ORDER_STATUSES
            }
        )


def _normalize_tickers(tickers: domain.Ticker) -> domain.Ticker:
    return domain.Ticker(tickers.removesuffix(_TINKOFF_ETF_SUFFIX))
