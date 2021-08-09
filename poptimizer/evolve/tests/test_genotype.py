"""Тестирование генотипа организма."""
import pytest

from poptimizer.evolve import genotype
from poptimizer.evolve.chromosomes import data

FAKE_GENES = (
    data.BATCH_SIZE,
    data.HISTORY_DAYS,
    data.TICKER_ON,
    data.DAY_OF_YEAR_ON,
    data.PRICES_ON,
    data.DIVIDENDS_ON,
    data.TURNOVER_ON,
    data.AVERAGE_TURNOVER_ON,
)


@pytest.fixture(scope="function", autouse=True)
def patch_features(monkeypatch):
    """Создает фиксированный генотип для тестов."""
    monkeypatch.setattr(genotype.ALL_CHROMOSOMES_TYPES[0], "_genes", FAKE_GENES)


def test_get_phenotype():
    """Проверка формирования фенотипа."""
    genotype_data = {"Data": {"batch_size": 3, "history_days": 4}}
    chromosomes_types = [data.Data]
    base_phenotype = {"type": "TestNet", "data": {"features": {"Prices": {"on": False}}}}
    gen = genotype.Genotype(genotype_data, base_phenotype, chromosomes_types)
    phenotype = gen.get_phenotype()
    assert phenotype["type"] == "TestNet"
    assert phenotype["data"]["batch_size"] == 3
    assert phenotype["data"]["history_days"] == 4
    assert phenotype["data"]["features"]["Prices"] == {"on": False}
    assert len(phenotype["data"]["features"]) == 6


def test_make_child_zero_scale():
    """При нулевом коэффициенте ребенок должен совпадать с родителем."""
    chromosomes_types = [data.Data]

    parent = {
        "Data": {
            "batch_size": 3.0,
            "history_days": 104.0,
            "ticker_on": 2.0,
            "day_of_year_on": 1.0,
            "prices_on": 0,
            "dividends_on": 3.0,
            "turnover_on": 1.0,
            "average_turnover_on": 1.0,
        },
    }
    base = {
        "Data": {
            "batch_size": 2,
            "history_days": 5,
            "ticker_on": 3,
            "day_of_year_on": 7,
            "prices_on": 8,
            "dividends_on": 4,
            "turnover_on": 6,
            "average_turnover_on": 4,
        },
    }

    parent = genotype.Genotype(parent, all_chromosome_types=chromosomes_types)
    base = genotype.Genotype(base, all_chromosome_types=chromosomes_types)

    child = parent.make_child(base, 0)

    assert isinstance(child, genotype.Genotype)
    assert child.data == parent.data
