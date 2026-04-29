import traceback as tb
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Protocol

from poptimizer.core import domain


class POError(Exception): ...


class DomainError(POError): ...


class TooShortHistoryError(DomainError):
    def __init__(self, ticker: domain.Ticker, minimal_returns_days: int) -> None:
        super().__init__(f"{ticker} has too short history - required {minimal_returns_days} returns")
        self.minimal_returns_days = minimal_returns_days


class UseCasesError(POError): ...


class AdapterError(POError): ...


class ControllersError(POError): ...


def get_root_poptimizer_error[E: POError](exc: E | ExceptionGroup[E]) -> E:
    while isinstance(exc, ExceptionGroup):
        exc = exc.exceptions[0]

    return exc


def get_root_error(exc: Exception | BaseExceptionGroup[Exception]) -> Exception:
    while isinstance(exc, BaseExceptionGroup):
        exc = exc.exceptions[0]

    return exc


class Warner(Protocol):
    def warning(self, msg: str, *args: Any) -> None: ...


@asynccontextmanager
async def suppress_poptimizer(warner: Warner, log_msg: str) -> AsyncGenerator[None]:
    try:
        yield
    except* POError as err:
        tb.print_exception(err, colorize=True)  # type: ignore[reportCallIssue]
        warner.warning(f"{log_msg} - {get_root_poptimizer_error(err)}")
