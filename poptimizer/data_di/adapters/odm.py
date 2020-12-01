"""Настройка мэппинга данных."""
from typing import Final

import pandas as pd

from poptimizer.data_di.adapters import mongo_server
from poptimizer.data_di.domain import factory
from poptimizer.data_di.shared import adapters

_DATA_DESCRIPTION: Final = (
    adapters.Desc(
        field_name="_df",
        doc_name="data",
        factory_name="df",
        encoder=lambda df: df.to_dict("split"),
        decoder=lambda doc_df: pd.DataFrame(**doc_df),
    ),
    adapters.Desc(
        field_name="_timestamp",
        doc_name="timestamp",
        factory_name="timestamp",
    ),
)


mongo_server.prepare_mongo_db_server()

MAPPER: Final = adapters.Mapper(_DATA_DESCRIPTION, factory.TablesFactory())
