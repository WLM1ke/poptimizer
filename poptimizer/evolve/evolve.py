"""Эволюция параметров модели и хранение в MongoDB."""
from typing import List, Type, Iterable, Optional, Tuple

import numpy as np
import pandas as pd

from poptimizer.dl.trainer2 import Trainer2
from poptimizer.evolve import genotype
from poptimizer.evolve.chromosomes.chromosome import ParamsType, Chromosome
from poptimizer.evolve.chromosomes.scheduler import Scheduler
from poptimizer.store.mongo import DB, MONGO_CLIENT

# Коллекция для хранения моделей
MODELS = "models"

# Метки ключей документа
ID = "_id"
GENOTYPE = "genotype"
SHARP = "sharpe"
MODEL = "model"
DATE = "date"

MAX_POPULATION = 100
BASE_PHENOTYPE = {
    "type": "WaveNet",
    "model": {
        "start_bn": True,
        "kernels": 2,
        "sub_blocks": 1,
        "gate_channels": 1,
        "residual_channels": 1,
        "skip_channels": 1,
        "end_channels": 1,
    },
    "optimizer": {"weight_decay": 0.01},
    "data": {
        "batch_size": 100,
        "history_days": 21,
        "forecast_days": 1,
        "features": {
            "Label": {"div_share": 0.9},
            "Prices": {},
            "Dividends": {},
            "Weight": {},
        },
    },
}
ALL_CHROMOSOMES_TYPES = [Scheduler]


class Evolution:
    """Эволюция параметров модели и хранение в MongoDB."""

    def __init__(
            self,
            base_phenotype: ParamsType,
            all_chromosome_types: List[Type[Chromosome]],
            max_population: int = MAX_POPULATION,
            db: str = DB,
            collection: str = MODELS,
    ):
        self._base_phenotype = base_phenotype
        self._all_chromosome_types = all_chromosome_types
        self._max_population = max_population
        self.collection = MONGO_CLIENT[db][collection]

        # Для реализации механизма эволюции нужно минимум 4 генотипа
        for i in range(4 - self.count):
            self._insert()

    @property
    def count(self) -> int:
        """Количество документов в коллекции."""
        return self.collection.count_documents({})

    def _insert(self, genotype_params: Optional[ParamsType] = None):
        genotype_params = genotype_params or {}
        doc = {GENOTYPE: genotype_params}
        self.collection.insert_one(doc)

    def _update(self, timestamp, sharpe, model):
        update = {"$set": {SHARP: sharpe, MODEL: model}}
        self.collection.update_one({ID: timestamp}, update)

    def _delete(self, timestamp):
        self.collection.delete_one({ID: timestamp})

    def sample(self, num: int) -> Iterable[ParamsType]:
        """Выбирает несколько случайных генотипов.

        Необходимо для реализации размножения и отбора.
        """
        return self.collection.aggregate([{"$sample": {"size": num}}])

    def mutate(self):
        """Осуществляет одну мутацию и сохраняет полученный генотип в MongoDB."""
        parents = self.sample(4)
        parents = [
            genotype.Genotype(sample[GENOTYPE], BASE_PHENOTYPE, ALL_CHROMOSOMES_TYPES)
            for sample in parents
        ]
        parent, *parents = parents
        gens_params = parent.mutate(*parents)
        print(gens_params)
        self._insert(gens_params)

    def selection(self, tickers: Tuple[str, ...], end: pd.Timestamp):
        """Осуществляет один отбор."""
        rivals = list(self.sample(2))
        scores = []
        models = []
        for doc in rivals:
            if doc.get(DATE) == end:
                scores.append(doc[SHARP])
                models.append(doc[MODEL])
                continue
            gen = genotype.Genotype(
                doc[GENOTYPE], BASE_PHENOTYPE, ALL_CHROMOSOMES_TYPES
            )
            phenotype = gen.phenotype
            model = doc.get(MODEL)
            trainer = Trainer2(tickers, end, phenotype, model)
            scores.append(trainer.sharpe)
            models.append(trainer.model)
        idx = np.argmax(scores)

        if rivals[idx].get(DATE) != end:
            self._update(rivals[idx][ID], sharpe=scores[idx], model=models[idx])
        self._delete(rivals[1 - idx][ID])

    def evolve(self, tickers: Tuple[str, ...], end: pd.Timestamp):
        """Осуществляет одну эпоху эволюции."""
        for step in range(1, self._max_population + 1):
            print(f"\nШаг эволюции - {step}/{self._max_population}:")
            excess = self.count - self._max_population
            if excess > 0:
                for death in range(excess):
                    self.selection(tickers, end)
            self.mutate()


if __name__ == "__main__":
    pos = dict(
        AKRN=7 + 715 + 88 + 4,
        ALRS=2690,
        BANE=0 + 236 + 84,
        BANEP=1097 + 13 + 107 + 235,
        BSPB=4890 + 0 + 3600 + 150,
        CBOM=0 + 4400 + 71000,
        CNTLP=0 + 0 + 0 + 9000,
        CHMF=0 + 730 + 170,
        DSKY=7180 + 740 + 6380 + 4320,
        GCHE=0 + 0 + 24,
        GMKN=0 + 109 + 1,
        IRKT=0 + 3000,
        KRKNP=66 + 0 + 43,
        KZOS=1200 + 5080 + 5190,
        LSNGP=2280 + 670 + 2410,
        LSRG=0 + 649 + 0 + 80,
        MGTSP=485 + 0 + 9,
        MOEX=2110 + 200 + 290,
        MRKV=0 + 9_680_000 + 1_420_000 + 1_300_000,
        MTSS=2340 + 4520 + 480 + 520,
        MVID=0 + 0 + 800,
        NMTP=29000 + 74000 + 13000 + 67000,
        PHOR=437 + 218 + 165 + 405,
        PIKK=0 + 3090 + 0 + 90,
        PLZL=86 + 21 + 23,
        PMSBP=0 + 0 + 1160,
        PRTK=0 + 6980,
        RNFT=0 + 51 + 11,
        RTKMP=0 + 29400,
        SNGSP=45200 + 5700 + 7700 + 2000,
        TRCN=41 + 0 + 4 + 3,
        UPRO=345_000 + 451_000 + 283_000 + 85000,
        VSMO=39 + 161 + 3,
        # Бумаги с нулевым весом
        TATNP=0,
        SIBN=0,
        RTKM=0,
        UNAC=0,
        MRKC=0,
        SELG=0,
        LSNG=0,
        MSRS=0,
        SVAV=0,
        TGKA=0,
        NKNC=0,
        NVTK=0,
        LKOH=0,
        OGKB=0,
        AFLT=0,
        SNGS=0,
        MRKZ=0,
        ROSN=0,
        SBERP=0,
        VTBR=0,
        ENRU=0,
        TATN=0,
        RASP=0,
        NLMK=0,
        NKNCP=0,
        FEES=0,
        HYDR=0,
        MRKP=0,
        MTLRP=0,
        MAGN=0,
        GAZP=0,
        SBER=0,
        MGNT=0,
        RSTI=0,
        MSNG=0,
        AFKS=0,
        SFIN=0,
        TRNFP=0,
        MTLR=0,
        ISKJ=0,
        TRMK=0,
        RSTIP=0,
        OBUV=0,
        APTK=0,
        LNZL=0,
        GTRK=0,
        ROLO=0,
        FESH=0,
        IRAO=0,
        AMEZ=0,
        YAKG=0,
        AQUA=0,
        RGSS=0,
        LIFE=0,
        KBTK=0,
        KMAZ=0,
        TTLK=0,
        TGKD=0,
    )
    ev = Evolution(BASE_PHENOTYPE, ALL_CHROMOSOMES_TYPES)
    ev.evolve(tuple(pos), pd.Timestamp("2020-03-27"))
