from datetime import date
from enum import StrEnum, auto

from poptimizer.domain import domain


class Theme(StrEnum):
    SYSTEM = auto()
    LIGHT = auto()
    DARK = auto()


class Settings(domain.Entity):
    theme: Theme = Theme.SYSTEM

    def update_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.day = date.today()
