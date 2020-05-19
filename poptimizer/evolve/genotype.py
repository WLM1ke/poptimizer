"""Класс генотипа и операций с ним."""
import copy
from collections import UserDict
from typing import List, Dict, Type, Optional

from poptimizer.dl import PhenotypeData
from poptimizer.evolve import chromosomes

# База для формирования фенотипа
BASE_PHENOTYPE = {
    "type": "WaveNet",
    "data": {
        "features": {
            "Label": {"div_share": 0.1},
            "Prices": {},
            "Dividends": {},
            "Turnover": {},
            "AverageTurnover": {},
            "DayOfYear": {},
            "Ticker": {},
        }
    },
}

# Все используемые хромосомы
ALL_CHROMOSOMES_TYPES = [
    chromosomes.Data,
    chromosomes.Model,
    chromosomes.Optimizer,
    chromosomes.Scheduler,
]

# Представление данных в генотипе
GenotypeData = Dict[str, chromosomes.ChromosomeData]


class Genotype(UserDict):
    """Класс генотипа.

    Умеет создавать фенотип для данного генотипа и осуществлять мутацию в рамках дифференциальной
    эволюции.
    """

    def __init__(
        self,
        genotype_data: GenotypeData = None,
        base_phenotype: Optional[PhenotypeData] = None,
        all_chromosome_types: Optional[List[Type[chromosomes.Chromosome]]] = None,
    ):
        super().__init__()

        genotype_data = genotype_data or {}
        all_chromosome_types = all_chromosome_types or ALL_CHROMOSOMES_TYPES

        for gen_type in all_chromosome_types:
            key = gen_type.__name__
            chromosome_data = genotype_data.get(key, dict())
            self.data[key] = gen_type(chromosome_data)

        self._base_phenotype = base_phenotype or BASE_PHENOTYPE

    def __str__(self) -> str:
        return "\n".join(f"{key}: {chromosome}" for key, chromosome in self.items())

    def get_phenotype(self) -> PhenotypeData:
        """Возвращает фенотип - параметры модели соответствующие набору генов."""
        phenotype = copy.deepcopy(self._base_phenotype)
        for chromosome in self.values():
            chromosome.change_phenotype(phenotype)
        return phenotype

    def make_child(
        self, base: "Genotype", diff1: "Genotype", diff2: "Genotype"
    ) -> "Genotype":
        """Реализует мутацию в рамках дифференциальной эволюции."""
        child = copy.deepcopy(self)
        for key in child:
            child[key] = self[key].make_child(base[key], diff1[key], diff2[key])
        return child
