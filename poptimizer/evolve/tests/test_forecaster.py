from collections import Iterable

import pandas as pd
import pytest

from poptimizer.dl import Forecast
from poptimizer.evolve import forecaster, store, population


@pytest.fixture(scope="module", autouse=True)
def set_test_collection():
    # noinspection PyProtectedMember
    saved_collection = store._COLLECTION
    test_collection = saved_collection.database["test"]
    store._COLLECTION = test_collection

    org = population.create_new_organism()
    org.evaluate_fitness(("TGKBP", "TRNFP"), pd.Timestamp("2020-05-23"))
    org = population.create_new_organism()
    org.evaluate_fitness(("TGKBP", "TRNFP"), pd.Timestamp("2020-05-23"))

    org = population.create_new_organism()
    org.evaluate_fitness(("TGKBP", "TRNFP"), pd.Timestamp("2020-05-22"))

    org = population.create_new_organism()
    org.evaluate_fitness(("AKRN", "TRNFP"), pd.Timestamp("2020-05-23"))

    yield

    store._COLLECTION = saved_collection
    test_collection.drop()


def forecasts_checkup(forecasts: forecaster.Forecasts):
    assert isinstance(forecasts, Iterable)
    assert forecasts.tickers == ("TGKBP", "TRNFP")
    assert forecasts.date == pd.Timestamp("2020-05-23")
    forecasts = list(forecasts)
    assert len(forecasts) == 3
    forecast = forecasts[0]
    assert isinstance(forecast, Forecast)
    assert forecast.tickers == ("TGKBP", "TRNFP")
    assert forecast.date == pd.Timestamp("2020-05-23")


def test_get_forecasts():
    forecasts = forecaster.get_forecasts(
        ("TGKBP", "TRNFP"), pd.Timestamp("2020-05-23")
    )

    forecasts_checkup(forecasts)


def test_get_forecasts_from_cache():
    forecasts = forecaster.get_forecasts(
        ("TGKBP", "TRNFP"), pd.Timestamp("2020-05-23")
    )

    forecasts_checkup(forecasts)
