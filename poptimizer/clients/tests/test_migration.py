import logging

import pytest
from pydantic import TypeAdapter

from poptimizer.adapters import mongo
from poptimizer.clients import migration
from poptimizer.fsm import tx


@pytest.mark.parametrize(
    ("last_version", "migrated"),
    [
        ("4.6.0", True),
        ("5.0.0", False),
    ],
)
async def test_the_portfolio_exclusions_move_to_settings_once(
    test_db: mongo.MongoDatabase,
    last_version: str,
    migrated: bool,  # noqa: FBT001
) -> None:
    await test_db["Portfolio"].insert_one({"_id": "Portfolio", "ver": 0, "exclude": ["GAZP", "SBER"]})
    store = mongo.Store(test_db)

    async with tx.Tx(logging.getLogger("test"), store, tx.Dispatcher()) as ctx:
        await migration.Client().migrate(ctx, last_version)

    settings = await test_db["Settings"].find_one({"_id": "Settings"})

    if not migrated:
        assert settings is None

        return

    assert settings is not None
    exclude = TypeAdapter(list[str]).validate_python(settings["exclude"])
    assert sorted(exclude) == ["GAZP", "SBER"]

    port = await test_db["Portfolio"].find_one({"_id": "Portfolio"})
    assert port is not None
    assert "exclude" not in port
