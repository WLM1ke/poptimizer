"""Интерфейсы шлюзов, используемые доменной моделью."""
import abc

import pandas as pd


class AbstractGateway(abc.ABC):
    """Загружает данные."""

    @abc.abstractmethod
    async def get(self) -> pd.DataFrame:
        """Загружает данные."""
