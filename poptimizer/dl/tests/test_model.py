import copy

import pandas as pd
import pytest
import torch

from poptimizer.dl import model
from poptimizer.dl.forecast import Forecast
from poptimizer.evolve import population
from poptimizer.evolve.population import TICKERS, DATE, MODEL
from poptimizer.store.mongo import MONGO_CLIENT

COLLECTION = MONGO_CLIENT["test"]["test"]


def test_normal_llh():
    m = torch.rand((100, 1))
    s = torch.tensor(0.5) + torch.rand((100, 1))
    x = dict(Label=torch.rand((100, 1)))
    llh, size = model.normal_llh((m, s), x)
    dist = torch.distributions.normal.Normal(m, s)
    assert llh.allclose(-dist.log_prob(x["Label"]).sum())
    assert size == 100


@pytest.fixture(scope="module", name="org")
def get_model_doc():
    org = population.create_new_organism(COLLECTION)
    org.evaluate_fitness(("KRKNP", "NMTP", "TATNP"), pd.Timestamp("2020-05-23"))
    yield org
    COLLECTION.drop()


def test_llh_from_trained_and_reloaded_model(org):
    gen = copy.deepcopy(org.genotype)
    # Для ускорения обучения
    gen["Scheduler"]["epochs"] /= 10
    phenotype = gen.get_phenotype()

    net = model.Model(org._data[TICKERS], org._data[DATE], phenotype, None)
    assert bytes(net) == bytes()

    llh = net.llh
    pickled_model = bytes(net)

    net = model.Model(org._data[TICKERS], org._data[DATE], phenotype, pickled_model)
    assert llh == net.llh
    assert bytes(net) == pickled_model

    # Из кеша
    assert llh == net.llh
    assert llh == net._eval_llh()


def test_raise_long_history(org):
    gen = copy.deepcopy(org.genotype)
    gen["Data"]["history_days"] *= 8
    phenotype = gen.get_phenotype()
    net = model.Model(org._data[TICKERS], org._data[DATE], phenotype, None)
    with pytest.raises(model.ModelError) as error:
        # noinspection PyStatementEffect
        net.llh
    assert issubclass(error.type, model.TooLongHistoryError)


def test_raise_gradient_error(org):
    gen = copy.deepcopy(org.genotype)
    gen["Scheduler"]["epochs"] /= 10
    gen["Scheduler"]["max_lr"] = 10
    phenotype = gen.get_phenotype()
    net = model.Model(org._data[TICKERS], org._data[DATE], phenotype, None)
    with pytest.raises(model.ModelError) as error:
        # noinspection PyStatementEffect
        net.llh
    assert issubclass(error.type, model.GradientsError)


def test_forecast(org):
    gen = copy.deepcopy(org.genotype)
    gen["Scheduler"]["epochs"] /= 10
    phenotype = gen.get_phenotype()
    net = model.Model(org._data[TICKERS], org._data[DATE], phenotype, org._data[MODEL])
    forecast = net.forecast()

    assert isinstance(forecast, Forecast)
    assert forecast.tickers == org._data[TICKERS]
    assert forecast.date == org._data[DATE]
    assert forecast.history_days == phenotype["data"]["history_days"]
    assert forecast.forecast_days == phenotype["data"]["forecast_days"]
    assert isinstance(forecast.mean, pd.Series)
    assert forecast.mean.index.tolist() == list(org._data[TICKERS])
    assert isinstance(forecast.std, pd.Series)
    assert forecast.std.index.tolist() == list(org._data[TICKERS])
