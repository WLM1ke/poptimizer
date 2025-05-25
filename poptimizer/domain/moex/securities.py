from enum import StrEnum, auto
from typing import Annotated, Final

from pydantic import AfterValidator, Field, PositiveInt

from poptimizer.domain import domain

_SHARES_BOARD: Final = "TQBR"
_PREFERRED_TYPE: Final = "2"
_PREFERRED_SUFFIX: Final = "P"


class IndustryIndex(StrEnum):
    UNKNOWN = auto()
    MOEXOG = auto()
    MOEXEU = auto()
    MOEXTL = auto()
    MOEXMM = auto()
    MOEXFN = auto()
    MOEXCN = auto()
    MOEXCH = auto()
    MOEXTN = auto()
    MOEXIT = auto()
    MOEXRE = auto()


class Row(domain.Row):
    ticker: domain.Ticker = Field(alias="SECID")
    lot: PositiveInt = Field(alias="LOTSIZE")
    isin: str = Field(alias="ISIN")
    board: str = Field(alias="BOARDID")
    type: str = Field(alias="SECTYPE")
    instrument: str = Field(alias="INSTRID")
    industry: IndustryIndex = IndustryIndex.UNKNOWN

    @property
    def is_share(self) -> bool:
        return self.board == _SHARES_BOARD

    @property
    def is_preferred(self) -> bool:
        return (self.type == _PREFERRED_TYPE) and self.is_share

    @property
    def ticker_base(self) -> str:
        if self.is_preferred:
            return self.ticker.removesuffix(_PREFERRED_SUFFIX)

        return self.ticker


class Securities(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(domain.sorted_with_ticker_field_validator),
    ] = Field(default_factory=list[Row])

    def update(self, update_day: domain.Day, rows: list[Row]) -> None:
        self.day = update_day

        self.df = sorted(rows, key=lambda sec: sec.ticker)
