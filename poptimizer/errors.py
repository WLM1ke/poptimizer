class POError(Exception): ...


class DomainError(POError): ...


class TooShortHistoryError(DomainError):
    def __init__(self, minimal_returns_days: int) -> None:
        super().__init__(f"too short history - required {minimal_returns_days} returns")
        self.minimal_returns_days = minimal_returns_days


class UseCasesError(POError): ...


class AdapterError(POError): ...


class ControllersError(POError): ...
