from typing import cast

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


def get_root_poptimizer_error(exc: POError | ExceptionGroup[POError]) -> POError:
    while not isinstance(exc, POError):
        exc = exc.exceptions[0]

    return exc


def get_root_error(exc: Exception | ExceptionGroup[Exception]) -> Exception:
    while isinstance(exc, ExceptionGroup):
        exc = cast("Exception", exc.exceptions[0])

    return exc
