"""Настройка мэппинга данных."""
from typing import Final

import pandas as pd
from motor import motor_asyncio

from poptimizer.data_di.domain import factory
from poptimizer.data_di.shared import adapters

# Асинхронный клиент для MongoDB
_MONGO_URI = "mongodb://localhost:27017"
MONGO_CLIENT: Final = motor_asyncio.AsyncIOMotorClient(_MONGO_URI, tz_aware=False)

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


MAPPER: Final = adapters.Mapper(
    MONGO_CLIENT,
    _DATA_DESCRIPTION,
    factory.TablesFactory(),
)
