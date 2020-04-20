import copy

import pymongo
import pytest

from poptimizer.dl import model
from poptimizer.evolve import genotype
from poptimizer.evolve.population import (
    COLLECTION,
    WINS,
    GENOTYPE,
    TICKERS,
    DATE,
    MODEL,
    INFORMATION_RATIO,
)

DB_PARAMS = {
    "filter": {WINS: {"$exists": True}},
    "sort": [(WINS, pymongo.DESCENDING)],
    "limit": 1,
}


@pytest.fixture(scope="module", name="doc")
def get_model_doc():
    return COLLECTION.find_one(**DB_PARAMS)


def test_ir_from_loaded_model(doc):
    phenotype = genotype.Genotype(doc[GENOTYPE]).get_phenotype()
    net = model.Model(doc[TICKERS], doc[DATE], phenotype, doc[MODEL])
    # Вычисление
    assert doc[INFORMATION_RATIO] == net.information_ratio
    # Из кеша
    assert doc[INFORMATION_RATIO] == net.information_ratio


def test_ir_from_trained_and_reloaded_model(doc):
    gen = copy.deepcopy(doc[GENOTYPE])
    # Для ускорения обучения
    gen["Scheduler"]["epochs"] /= 10
    phenotype = genotype.Genotype(gen).get_phenotype()
    net = model.Model(doc[TICKERS], doc[DATE], phenotype, None)
    assert net.pickled_model is None

    ir = net.information_ratio
    pickled_model = net.pickled_model

    net = model.Model(doc[TICKERS], doc[DATE], phenotype, pickled_model)
    assert ir == net.information_ratio


def test_raise_long_history(doc):
    gen = copy.deepcopy(doc[GENOTYPE])
    gen["Data"]["history_days"] *= 2
    phenotype = genotype.Genotype(gen).get_phenotype()
    net = model.Model(doc[TICKERS], doc[DATE], phenotype, None)
    with pytest.raises(model.ModelError) as error:
        # noinspection PyStatementEffect
        net.information_ratio
    assert issubclass(error.type, model.TooLongHistoryError)


def test_raise_gradient_error(doc):
    gen = copy.deepcopy(doc[GENOTYPE])
    gen["Scheduler"]["epochs"] /= 10
    gen["Scheduler"]["max_lr"] *= 100
    phenotype = genotype.Genotype(gen).get_phenotype()
    net = model.Model(doc[TICKERS], doc[DATE], phenotype, None)
    with pytest.raises(model.ModelError) as error:
        # noinspection PyStatementEffect
        net.information_ratio
    assert issubclass(error.type, model.GradientsError)
