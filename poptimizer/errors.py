from poptimizer.domain import domain


class POError(Exception): ...


class DomainError(POError): ...


class TooShortHistoryError(DomainError):
    def __init__(self, ticker: domain.Ticker, minimal_returns_days: int) -> None:
        super().__init__(f"{ticker} has too short history - required {minimal_returns_days} returns")
        self.minimal_returns_days = minimal_returns_days


class UseCasesError(POError): ...


class AdapterError(POError): ...


class ControllersError(POError): ...
