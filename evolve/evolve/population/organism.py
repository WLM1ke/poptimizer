from __future__ import annotations

from dataclasses import dataclass

import bson
import pandas as pd
from typing import ClassVar

from evolve.population.gene import GenePool, Genotype


@dataclass(kw_only=True, slots=True)
class Organism:
    """Организм."""

    gene_pool: ClassVar[GenePool] = GenePool()

    id: bson.ObjectId
    gen: Genotype
    timestamp: pd.Timestamp | None = None

    @classmethod
    def new(cls) -> Organism:
        """Создает организм по умолчанию для на основе генофонда."""
        return Organism(id=bson.ObjectId(), gen=cls.gene_pool.new())

    def breed(self, scale: float, parent1: Organism, parent2: Organism) -> Organism:
        """Создает потомка организма."""
        child_gen = self.gene_pool.breed(
            self.gen,
            scale,
            parent1.gen,
            parent2.gen,
        )

        return Organism(id=bson.ObjectId(), gen=child_gen)
