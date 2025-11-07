from datetime import date
from enum import StrEnum, auto

from poptimizer.domain import domain


class Theme(StrEnum):
    SYSTEM = auto()
    LIGHT = auto()
    DARK = auto()


class Settings(domain.Entity):
    theme: Theme = Theme.SYSTEM
    hide_zero_positions: bool = False

    def update_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.day = date.today()

    def update_hide_zero_positions(self, *, hide: bool) -> None:
        self.hide_zero_positions = hide
        self.day = date.today()
