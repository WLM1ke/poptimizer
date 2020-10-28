"""Преобразования типов во время загрузки данных  из MongoDB."""
from typing import Final

import pandas as pd

from poptimizer.data_di.shared.mapping import Desc

# Описание мэппинга данных в MongoDB
DATA_MAPPING: Final = (
    Desc(
        field_name="_df",
        doc_name="data",
        factory_name="df",
        encoder=lambda df: df.to_dict("split"),
        decoder=lambda doc_df: pd.DataFrame(**doc_df),
    ),
    Desc(
        field_name="_timestamp",
        doc_name="timestamp",
        factory_name="timestamp",
    ),
)
