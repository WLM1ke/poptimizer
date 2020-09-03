import datetime

import pytest


from poptimizer.data.config import bootstrap


@pytest.fixture(scope="function", autouse=True)
def set_start_date(monkeypatch):
    monkeypatch.setattr(
        bootstrap,
        "START_DATE",
        datetime.date(2010, 1, 1),
    )
    yield
