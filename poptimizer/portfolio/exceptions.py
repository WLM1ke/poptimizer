"""Ошибки, связанные с операциями с портфелем."""
from poptimizer.core import exceptions


class PortfolioError(exceptions.POError):
    """Базовая ошибка, связанная с изменением информации о портфеле."""


class PortfolioUpdateError(PortfolioError):
    """Ошибка сервисов обновления портфеля."""


class PortfolioEditError(PortfolioError):
    """Ошибка сервисов редактирования портфеля."""
