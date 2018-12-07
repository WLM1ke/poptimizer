"""Ошибки и основные метки данных"""

__all__ = ["POptimizerError", "CASH", "PORTFOLIO"]


class POptimizerError(Exception):
    """Базовое исключение"""

    pass


CASH = "CASH"
PORTFOLIO = "PORTFOLIO"
