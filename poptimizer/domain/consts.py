from datetime import date
from typing import Final


class POError(Exception):
    def __str__(self) -> str:
        """Выводи исходную причину ошибки при ее наличии для удобства логирования.

        https://peps.python.org/pep-3134/
        """
        errs = [repr(self)]
        cause_err: BaseException | None = self

        while cause_err := cause_err and (cause_err.__cause__ or cause_err.__context__):
            errs.append(repr(cause_err))

        return " -> ".join(errs)


class DomainError(POError): ...


# Дата, с которой собираются дивиденды
START_DAY: Final = date(2015, 1, 1)
AFTER_TAX: Final = 0.85
