import pytest

from poptimizer.data import config


@pytest.fixture(scope="function", autouse=True)
def set_start_date(monkeypatch):
    monkeypatch.setattr(
        config,
        "CONFIG",
        config.app.Config(
            db_session=config.db.MongoDBSession(),
            description_registry=config.TABLES_REGISTRY,
            start_date=config.datetime.date(2010, 1, 1),
        ),
    )
    yield
