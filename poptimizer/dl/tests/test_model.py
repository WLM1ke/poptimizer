import copy

import pandas as pd
import pymongo
import pytest
import torch

from poptimizer.dl import model
from poptimizer.dl.forecast import Forecast
from poptimizer.evolve import genotype
from poptimizer.evolve.population import (
    COLLECTION,
    WINS,
    GENOTYPE,
    TICKERS,
    DATE,
    MODEL,
)

DB_PARAMS = {
    "filter": {WINS: {"$exists": True}},
    "sort": [(WINS, pymongo.DESCENDING)],
    "limit": 1,
}


def test_normal_llh():
    m = torch.rand((100, 1))
    s = torch.tensor(0.5) + torch.rand((100, 1))
    x = dict(Label=torch.rand((100, 1)))
    llh, size = model.normal_llh((m, s), x)
    dist = torch.distributions.normal.Normal(m, s)
    assert llh.allclose(-dist.log_prob(x["Label"]).sum())
    assert size == 100


@pytest.fixture(scope="module", name="doc")
def get_model_doc():
    return COLLECTION.find_one(**DB_PARAMS)


def test_llh_from_trained_and_reloaded_model(doc):
    gen = copy.deepcopy(doc[GENOTYPE])
    # Для ускорения обучения
    gen["Scheduler"]["epochs"] /= 10
    phenotype = genotype.Genotype(gen).get_phenotype()

    net = model.Model(doc[TICKERS], doc[DATE], phenotype, None)
    assert bytes(net) == bytes()

    llh = net.llh
    pickled_model = bytes(net)

    net = model.Model(doc[TICKERS], doc[DATE], phenotype, pickled_model)
    assert llh == net.llh
    assert bytes(net) == pickled_model

    # Из кеша
    assert llh == net.llh
    assert llh == net._eval_llh()


def test_raise_long_history(doc):
    gen = copy.deepcopy(doc[GENOTYPE])
    gen["Data"]["history_days"] *= 2
    phenotype = genotype.Genotype(gen).get_phenotype()
    net = model.Model(doc[TICKERS], doc[DATE], phenotype, None)
    with pytest.raises(model.ModelError) as error:
        # noinspection PyStatementEffect
        net.llh
    assert issubclass(error.type, model.TooLongHistoryError)


def test_raise_gradient_error(doc):
    gen = copy.deepcopy(doc[GENOTYPE])
    gen["Scheduler"]["epochs"] /= 10
    gen["Scheduler"]["max_lr"] = 10
    phenotype = genotype.Genotype(gen).get_phenotype()
    net = model.Model(doc[TICKERS], doc[DATE], phenotype, None)
    with pytest.raises(model.ModelError) as error:
        # noinspection PyStatementEffect
        net.llh
    assert issubclass(error.type, model.GradientsError)


def test_forecast(doc):
    gen = copy.deepcopy(doc[GENOTYPE])
    gen["Scheduler"]["epochs"] /= 10
    phenotype = genotype.Genotype(gen).get_phenotype()
    net = model.Model(doc[TICKERS], doc[DATE], phenotype, doc[MODEL])
    forecast = net.forecast()

    assert isinstance(forecast, Forecast)
    assert forecast.tickers == doc[TICKERS]
    assert forecast.date == doc[DATE]
    assert forecast.history_days == phenotype["data"]["history_days"]
    assert forecast.forecast_days == phenotype["data"]["forecast_days"]
    assert isinstance(forecast.mean, pd.Series)
    assert forecast.mean.index.tolist() == list(doc[TICKERS])
    assert isinstance(forecast.std, pd.Series)
    assert forecast.std.index.tolist() == list(doc[TICKERS])
