"""Описание доменных объектов."""
from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True, frozen=True)
class Table:
    """Таблица с рыночными данными."""

    group: str
    name: str | None
    timestamp: pd.Timestamp | None
    df: pd.DataFrame | None
