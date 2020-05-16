import copy

import numpy as np
import pymongo
import pytest
import torch

from poptimizer.dl import model
from poptimizer.evolve import genotype
from poptimizer.evolve.population import COLLECTION, WINS, GENOTYPE, TICKERS, DATE

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


def test_incremental_return():
    a = np.array([1, 2, 1, 2])
    b = np.array([2, 3, 4, 1])
    c = np.array([2, 4, 6, 7])
    assert model.incremental_return(c, a, b ** 2) == pytest.approx(1.9260727134667)
    assert model.incremental_return(c, b, a ** 2) == pytest.approx(1.55613358171397)
    assert model.incremental_return(b, a, c ** 2) == pytest.approx(0.0777498264601518)


@pytest.fixture(scope="module", name="doc")
def get_model_doc():
    return COLLECTION.find_one(**DB_PARAMS)


def test_ir_from_trained_and_reloaded_model(doc):
    gen = copy.deepcopy(doc[GENOTYPE])
    # Для ускорения обучения
    gen["Scheduler"]["epochs"] /= 10
    phenotype = genotype.Genotype(gen).get_phenotype()

    net = model.Model(doc[TICKERS], doc[DATE], phenotype, None)
    ir = net.llh
    pickled_model = bytes(net)

    net = model.Model(doc[TICKERS], doc[DATE], phenotype, pickled_model)
    assert ir == net.llh
    # Из кеша
    assert ir == net.llh


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
    gen["Scheduler"]["max_lr"] = 1
    phenotype = genotype.Genotype(gen).get_phenotype()
    with pytest.raises(model.ModelError) as error:
        model.Model(doc[TICKERS], doc[DATE], phenotype, None)
    assert issubclass(error.type, model.GradientsError)
