from enum import StrEnum, auto
from typing import Annotated, Final, NewType

from pydantic import AfterValidator, BaseModel, Field, PositiveInt

from poptimizer.core import domain

_SHARES_BOARD: Final = "TQBR"
_PREFERRED_TYPE: Final = "2"
_PREFERRED_SUFFIX: Final = "P"


class SectorIndex(StrEnum):
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


Sector = NewType("Sector", str)
OtherShare: Final = Sector("Other share")
OtherETF: Final = Sector("Other ETF")


class SectorIndexRow(BaseModel):
    ticker: domain.Ticker
    till: domain.Day


class ETFAttr(BaseModel):
    name: str


class ETFRow(BaseModel):
    ticker: domain.Ticker
    sub_class: ETFAttr = Field(alias="assetSubClass")
    currency: ETFAttr = Field(alias="currency")

    @property
    def sector(self) -> Sector:
        return Sector(f"{self.sub_class.name} - {self.currency.name}")


class Security(domain.Row):
    ticker: domain.Ticker = Field(alias="SECID")
    lot: PositiveInt = Field(alias="LOTSIZE")
    isin: str = Field(alias="ISIN")
    board: str = Field(alias="BOARDID")
    type: str = Field(alias="SECTYPE")
    instrument: str = Field(alias="INSTRID")
    sector: Sector = OtherShare

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
        list[Security],
        AfterValidator(domain.sorted_with_ticker_field_validator),
    ] = Field(default_factory=list[Security])

    def update(self, rows: list[Security]) -> None:
        self.df = sorted(rows, key=lambda sec: sec.ticker)
