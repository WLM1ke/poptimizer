import datetime

import pytest


from poptimizer.data import config


@pytest.fixture(scope="function", autouse=True)
def set_start_date(monkeypatch):
    monkeypatch.setattr(
        config,
        "START_DATE",
        datetime.date(2010, 1, 1),
    )
    yield
