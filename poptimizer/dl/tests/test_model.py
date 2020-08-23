import copy

import pandas as pd
import pytest
import torch

from poptimizer.dl import model
from poptimizer.dl.forecast import Forecast
from poptimizer.evolve import population, store


def test_normal_llh():
    m = torch.rand((100, 1))
    s = torch.tensor(0.5) + torch.rand((100, 1))
    x = dict(Label=torch.rand((100, 1)))
    llh, size, llh_all = model.normal_llh((m, s), x)
    dist = torch.distributions.normal.Normal(m, s)
    assert llh.allclose(-dist.log_prob(x["Label"]).sum())
    assert llh_all.allclose(dist.log_prob(x["Label"]))
    assert size == 100


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

    net = model.Model(tuple(org._data.tickers), org._data.date, phenotype, None)
    assert bytes(net) == bytes()

    llh = net.llh
    pickled_model = bytes(net)

    net = model.Model(tuple(org._data.tickers), org._data.date, phenotype, pickled_model)
    assert llh == net.llh
    assert bytes(net) == pickled_model

    # Из кеша
    assert llh == net.llh
    assert llh == net._eval_llh()


def test_raise_gradient_error(org):
    gen = copy.deepcopy(org.genotype)
    gen["Scheduler"]["epochs"] /= 10
    gen["Scheduler"]["max_lr"] = 10
    phenotype = gen.get_phenotype()
    net = model.Model(tuple(org._data.tickers), org._data.date, phenotype, None)
    with pytest.raises(model.ModelError) as error:
        # noinspection PyStatementEffect
        net.llh
    assert issubclass(error.type, model.GradientsError)


def test_forecast(org):
    gen = copy.deepcopy(org.genotype)
    gen["Scheduler"]["epochs"] /= 10
    phenotype = gen.get_phenotype()
    net = model.Model(tuple(org._data.tickers), org._data.date, phenotype, org._data.model)
    forecast = net.forecast()

    assert isinstance(forecast, Forecast)
    assert forecast.tickers == tuple(org._data.tickers)
    assert forecast.date == org._data.date
    assert forecast.history_days == phenotype["data"]["history_days"]
    assert isinstance(forecast.mean, pd.Series)
    assert forecast.mean.index.tolist() == list(org._data.tickers)
    assert isinstance(forecast.std, pd.Series)
    assert forecast.std.index.tolist() == list(org._data.tickers)
