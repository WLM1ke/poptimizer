import datetime

import pytest

import poptimizer.data.ports.outer
from poptimizer.data import config


@pytest.fixture(scope="function", autouse=True)
def set_start_date(monkeypatch):
    app_conf = config.get()
    monkeypatch.setattr(
        config,
        "CONFIG",
        poptimizer.data.ports.outer.Config(
            event_bus=app_conf.event_bus,
            viewer=app_conf.viewer,
            start_date=datetime.date(2010, 1, 1),
        ),
    )
    yield
