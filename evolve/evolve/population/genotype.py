"""Генотип и операции с ним."""
import collections
import types
from typing import ClassVar

from evolve.population import data, gene


class Genotype(collections.UserDict[str, dict[str, float]]):
    """Описание генотипа конкретного организма.

    Генотип состоит из отдельных хромосом - групп связанных генов.
    Значение генов представлены float для осуществления дифференциальной эволюции.
    """

    genotype: ClassVar[gene.GenoPool] = types.MappingProxyType({"data": data.chromosome()})

    def make_child(self, parent1: "Genotype", parent2: "Genotype", scale: float) -> "Genotype":
        """Создает генотип ребенка."""
        child: Genotype = Genotype()

        for key_chromosome, chromosome in self.genotype.items():
            child[key_chromosome] = {}
            for key_gen, gen in chromosome.items():
                child[key_chromosome][key_gen] = gen.make_child(
                    self.get(key_chromosome, {}).get(key_gen, gen.default()),
                    parent1.get(key_chromosome, {}).get(key_gen, gen.default()),
                    parent2.get(key_chromosome, {}).get(key_gen, gen.default()),
                    scale,
                )

        return child
