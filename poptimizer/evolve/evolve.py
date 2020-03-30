"""Эволюция параметров модели и хранение в MongoDB."""
from typing import List, Type, Iterable, Optional, Tuple

import pandas as pd

from poptimizer.dl.trainer2 import Trainer2
from poptimizer.evolve import genotype
from poptimizer.evolve.chromosomes.chromosome import ParamsType, Chromosome
from poptimizer.evolve.chromosomes.data import Data
from poptimizer.evolve.chromosomes.model import Model
from poptimizer.evolve.chromosomes.optimizer import Optimizer
from poptimizer.evolve.chromosomes.scheduler import Scheduler
from poptimizer.store.mongo import DB, MONGO_CLIENT

# Коллекция для хранения моделей
MODELS = "models"

# Метки ключей документа
ID = "_id"
GENOTYPE = "genotype"
MODEL = "model"
SHARPE = "sharpe"
SHARPE_DATE = "sharpe_date"

MAX_POPULATION = 100
BASE_PHENOTYPE = {
    "type": "WaveNet",
    "data": {
        "features": {
            "Label": {"div_share": 0.9},
            "Prices": {},
            "Dividends": {},
            "Weight": {},
        }
    },
}
ALL_CHROMOSOMES_TYPES = [Scheduler, Data, Model, Optimizer]


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

    def _update(self, object_id, update):
        update = {"$set": update}
        self.collection.update_one({ID: object_id}, update)

    def _delete(self, object_id):
        self.collection.delete_one({ID: object_id})

    def min_max_sharp(self) -> Tuple[Optional[float], Optional[float]]:
        """Находит минимальное и максимальное значение коэффициента Шарпа."""
        rez = (
            list(
                self.collection.find(
                    {SHARPE: {"$exists": True}}, sort=[(SHARPE, 1)], limit=1
                )
            ),
            list(
                self.collection.find(
                    {SHARPE: {"$exists": True}}, sort=[(SHARPE, -1)], limit=1
                )
            ),
        )
        if len(rez[0]) == 0:
            return None, None

        # noinspection PyTypeChecker
        return tuple(i[SHARPE] for i, *_ in rez)

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
        self._insert(gens_params)
        return gens_params

    def selection(self, tickers: Tuple[str, ...], end: pd.Timestamp):
        """Осуществляет один отбор."""
        rivals = list(self.sample(2))
        for num, rival in enumerate(rivals, 1):
            print(f"{num}: Генотип")
            self.print_gens_params(rival[GENOTYPE])
            if rival.get(SHARPE_DATE) != end:
                model_state_dict = rival.get(MODEL)
                phenotype = genotype.Genotype(
                    rival[GENOTYPE], BASE_PHENOTYPE, ALL_CHROMOSOMES_TYPES
                ).phenotype
                model = Trainer2(tickers, end, phenotype, model_state_dict)

                update = dict()
                update[SHARPE] = model.sharpe
                update[SHARPE_DATE] = end
                if not model_state_dict:
                    update[MODEL] = model.model
                self._update(rival[ID], update)
                rival.update(update)
            print(f"Коэффициент Шарапа - {rival[SHARPE]:.4f}\n")

        num, _ = max(enumerate(rivals), key=lambda x: x[1][SHARPE])
        self._delete(rivals[1 - num][ID])

    def evolve(self, tickers: Tuple[str, ...], end: pd.Timestamp):
        """Осуществляет одну эпоху эволюции."""
        for step in range(1, self._max_population + 1):
            print(f"***Шаг эпохи - {step}/{self._max_population}***")
            print(
                f"Значения коэффициента Шарпа лежат в интервале {self.min_max_sharp()}\n"
            )
            print("Мутация")
            gens_params = self.mutate()
            print(f"Генотип")
            self.print_gens_params(gens_params)

            excess = self.count - self._max_population
            if excess > 0:
                for death in range(1, excess + 1):
                    print(f"Отбор - {death}/{excess}")
                    self.selection(tickers, end)

    @staticmethod
    def print_gens_params(param):
        """Распечатка генотипа."""
        for key, val in param.items():
            print(f"{key}: {val}")
        print()


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
        TGKB=0,
    )
    ev = Evolution(BASE_PHENOTYPE, ALL_CHROMOSOMES_TYPES)
    ev.evolve(tuple(pos), pd.Timestamp("2020-03-27"))
