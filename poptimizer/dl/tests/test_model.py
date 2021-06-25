import copy

import pandas as pd
import pytest

from poptimizer.dl import model
from poptimizer.dl.forecast import Forecast
from poptimizer.evolve import population, store


@pytest.fixture(scope="module", name="org")
def get_model_doc():
    # noinspection PyProtectedMember
    saved_collection = store._COLLECTION
    test_collection = saved_collection.database["test"]
    store._COLLECTION = test_collection

    org = population.create_new_organism()
    org.evaluate_fitness(("KRKNP", "NMTP", "TATNP"), pd.Timestamp("2020-05-23"))

    yield org

    store._COLLECTION = saved_collection
    test_collection.drop()


def test_llh_from_trained_and_reloaded_model(org):
    gen = copy.deepcopy(org.genotype)
    # Для ускорения обучения
    gen["Scheduler"]["epochs"] /= 10
    phenotype = gen.get_phenotype()

    net = model.Model(tuple(org._doc.tickers), org._doc.date, phenotype, None)
    assert bytes(net) == bytes()

    llh = net.quality_metrics
    pickled_model = bytes(net)

    net = model.Model(tuple(org._doc.tickers), org._doc.date, phenotype, pickled_model)
    assert llh == net.quality_metrics
    assert bytes(net) == pickled_model

    # Из кеша
    assert llh == net.quality_metrics
    assert llh == net._eval_llh()


def test_forecast(org):
    gen = copy.deepcopy(org.genotype)
    gen["Scheduler"]["epochs"] /= 10
    phenotype = gen.get_phenotype()
    net = model.Model(tuple(org._doc.tickers), org._doc.date, phenotype, org._doc.model)
    forecast = net.forecast()

    assert isinstance(forecast, Forecast)
    assert forecast.tickers == tuple(org._doc.tickers)
    assert forecast.date == org._doc.date
    assert forecast.history_days == phenotype["data"]["history_days"]
    assert isinstance(forecast.mean, pd.Series)
    assert forecast.mean.index.tolist() == list(org._doc.tickers)
    assert isinstance(forecast.std, pd.Series)
    assert forecast.std.index.tolist() == list(org._doc.tickers)
