from collections.abc import AsyncGenerator
from typing import Final

import pytest
from pydantic import MongoDsn

from poptimizer.adapters import mongo

_TEST_DB: Final = "poptimizer-test"
_URI: Final = MongoDsn("mongodb://localhost:27017")


@pytest.fixture(name="test_db")
async def make_test_db() -> AsyncGenerator[mongo.MongoDatabase]:
    async with mongo.db(_URI, _TEST_DB) as db:
        await db.client.drop_database(_TEST_DB)
        yield db
        await db.client.drop_database(_TEST_DB)
