"""Класс генотипа и операций с ним."""
import copy
import types
from collections import UserDict
from typing import Optional, Type

from poptimizer.dl import PhenotypeData
from poptimizer.evolve import chromosomes

# Базовый генотип, к которому добавляются хромосомы
BASE_PHENOTYPE = types.MappingProxyType(
    {
        "type": "WaveNet",
        "data": {"features": {"Label": {"on": True}}},
    },
)

# Все используемые хромосомы
ALL_CHROMOSOMES_TYPES = (
    chromosomes.Data,
    chromosomes.Model,
    chromosomes.Optimizer,
    chromosomes.Scheduler,
    chromosomes.Utility,
)

# Представление данных в генотипе
GenotypeData = dict[str, chromosomes.ChromosomeData]
GenotypeTypes = list[Type[chromosomes.Chromosome]]


class Genotype(UserDict):
    """Класс генотипа.

    Умеет создавать фенотип для данного генотипа и осуществлять мутацию в рамках дифференциальной
    эволюции.
    """

    def __init__(
        self,
        genotype_data: GenotypeData = None,
        base_phenotype: Optional[PhenotypeData] = None,
        all_chromosome_types: Optional[GenotypeTypes] = None,
    ):
        """Инициализирует значения всех генов."""
        super().__init__()

        genotype_data = genotype_data or {}
        all_chromosome_types = all_chromosome_types or list(ALL_CHROMOSOMES_TYPES)

        for gen_type in all_chromosome_types:
            key = gen_type.__name__
            chromosome_data = genotype_data.get(key, {})
            self.data[key] = gen_type(chromosome_data)

        self._base_phenotype = base_phenotype or dict(BASE_PHENOTYPE)

    def __str__(self) -> str:
        """Текстовое представление хромосом в отдельных строчках."""
        text_chromosome = [f"{key}: {chromosome}" for key, chromosome in self.items()]
        return "\n".join(text_chromosome)

    def get_phenotype(self) -> PhenotypeData:
        """Возвращает фенотип — параметры модели соответствующие набору генов."""
        phenotype = copy.deepcopy(self._base_phenotype)
        for chromosome in self.values():
            chromosome.change_phenotype(phenotype)
        return phenotype

    def make_child(
        self,
        parent1: "Genotype",
        parent2: "Genotype",
        scale: float,
    ) -> "Genotype":
        """Реализует мутацию в рамках дифференциальной эволюции отдельных хромосом."""
        child = copy.deepcopy(self)
        for key in child:
            child[key] = self[key].make_child(parent1[key], parent2[key], scale)
        return child
