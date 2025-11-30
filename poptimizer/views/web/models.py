from enum import StrEnum, auto
from typing import Self

from aiohttp import web
from pydantic import BaseModel


class Theme(StrEnum):
    SYSTEM = auto()
    LIGHT = auto()
    DARK = auto()


class Cookie(BaseModel):
    theme: Theme = Theme.SYSTEM
    hide_zero_positions: bool = False

    def toggle_zero_positions(self) -> None:
        self.hide_zero_positions = not self.hide_zero_positions

    @classmethod
    def from_request(cls, req: web.Request) -> Self:
        return cls.model_validate(req.cookies)
