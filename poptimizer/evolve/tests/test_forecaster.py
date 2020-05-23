from collections import Iterable

import pandas as pd
import pytest

from poptimizer.dl import Forecast
from poptimizer.evolve import population, forecaster
from poptimizer.store.mongo import MONGO_CLIENT

COLLECTION = MONGO_CLIENT["test"]["test"]


@pytest.fixture(scope="module", autouse=True)
def prepare_forecasts():
    population.create_new_organism(COLLECTION)

    org = population.create_new_organism(COLLECTION)
    org.evaluate_fitness(("TGKBP", "TRNFP"), pd.Timestamp("2020-05-23"))
    org = population.create_new_organism(COLLECTION)
    org.evaluate_fitness(("TGKBP", "TRNFP"), pd.Timestamp("2020-05-23"))

    org = population.create_new_organism(COLLECTION)
    org.evaluate_fitness(("TGKBP", "TRNFP"), pd.Timestamp("2020-05-22"))

    org = population.create_new_organism(COLLECTION)
    org.evaluate_fitness(("AKRN", "TRNFP"), pd.Timestamp("2020-05-23"))

    yield

    COLLECTION.drop()


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
        ("TGKBP", "TRNFP"), pd.Timestamp("2020-05-23"), COLLECTION
    )

    forecasts_checkup(forecasts)


def test_get_forecasts_from_cache():
    forecasts = forecaster.get_forecasts(
        ("TGKBP", "TRNFP"), pd.Timestamp("2020-05-23"), COLLECTION
    )

    forecasts_checkup(forecasts)
