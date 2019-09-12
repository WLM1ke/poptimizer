"""Менеджеры данных для котировок, индекса и перечня торгуемых бумаг с MOEX."""
from typing import Optional, Any, List, Dict

import apimoex

from poptimizer.config import POptimizerError
from poptimizer.store import utils_new, manager_new
from poptimizer.store.manager_new import AbstractManager

# Наименование данных по акциям
SECURITIES = "securities"


class Securities(AbstractManager):
    """Информация о всех торгующихся акциях.

    При появлении новой информации создается с нуля, так как перечень торгуемых акций может как
    расширяться, так и сокращаться, а характеристики отдельных акций (например, размер лота) меняться
    со временем.
    """

    def __init__(self, db=utils_new.DB) -> None:
        super().__init__(
            collection=utils_new.MISC,
            db=db,
            create_from_scratch=True,
            index=utils_new.TICKER,
        )

    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        """Загружает полностью данные о всех торгующихся акциях."""
        if item != SECURITIES:
            raise POptimizerError(
                f"Отсутствуют данные {self._collection.full_name}.{item}"
            )
        columns = ("SECID", "REGNUMBER", "LOTSIZE")
        data = apimoex.get_board_securities(self._session, columns=columns)
        formatters = dict(
            SECID=lambda x: (utils_new.TICKER, x),
            REGNUMBER=lambda x: (utils_new.REG_NUMBER, x),
            LOTSIZE=lambda x: (utils_new.LOT_SIZE, x),
        )
        return manager_new.data_formatter(data, formatters)
