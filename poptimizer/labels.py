"""Основные метки данных"""
import enum


class Labels(enum.Enum):
    """Метки используемые для специальных полей в данных"""

    CASH = "CASH"
    PORTFOLIO = "PORTFOLIO"

    def __str__(self):
        return self.value
