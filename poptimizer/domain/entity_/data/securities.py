import itertools
from typing import Final

from pydantic import Field, field_validator

from poptimizer.domain.entity_ import entity

_SHARES_BOARD: Final = "TQBR"
_PREFERRED_TYPE: Final = "2"
_PREFERRED_SUFFIX: Final = "P"


class Row(entity.Row):
    ticker: entity.Ticker = Field(alias="SECID")
    lot: int = Field(alias="LOTSIZE")
    isin: str = Field(alias="ISIN")
    board: str = Field(alias="BOARDID")
    type: str = Field(alias="SECTYPE")
    instrument: str = Field(alias="INSTRID")

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


class Securities(entity.Entity):
    df: list[Row] = Field(default_factory=list[Row])

    def update(self, update_day: entity.Day, rows: list[Row]) -> None:
        self.day = update_day

        rows.sort(key=lambda sec: sec.ticker)

        self.df = rows

    @field_validator("df")
    def _must_be_sorted_by_ticker(cls, df: list[Row]) -> list[Row]:
        ticker_pairs = itertools.pairwise(row.ticker for row in df)

        if not all(ticker < next_ for ticker, next_ in ticker_pairs):
            raise ValueError("tickers are not sorted")

        return df
