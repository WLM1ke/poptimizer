"""Описание доменных объектов."""
from dataclasses import dataclass
from enum import unique, Enum

import pandas as pd


@unique
class Group(Enum):
    TRADING_DATE = "trading_date"


@dataclass(slots=True, frozen=True, kw_only=True)
class Table:
    """Таблица с рыночными данными."""

    group: Group
    name: str | None
    timestamp: pd.Timestamp | None
    df: pd.DataFrame | None
