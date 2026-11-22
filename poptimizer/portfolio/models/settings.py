from typing import Annotated

from pydantic import Field, PlainSerializer

from poptimizer.core import domain


class Settings(domain.Entity):
    exclude: Annotated[
        set[domain.Ticker],
        PlainSerializer(
            list,
            return_type=list[domain.Ticker],
        ),
    ] = Field(default_factory=set[domain.Ticker])
