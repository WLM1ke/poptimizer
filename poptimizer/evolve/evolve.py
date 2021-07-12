"""Эволюция параметров модели."""
import numpy as np
from scipy import stats

from poptimizer import config
from poptimizer.data.views import listing
from poptimizer.dl import ModelError
from poptimizer.evolve import population
from poptimizer.portfolio.portfolio import load_from_yaml

# Понижение масштаба разницы между родителями после возникновения ошибки
SCALE_DOWN = 0.95


class Evolution:
    """Эволюция параметров модели.

    Эволюция бесконечный процесс обновления параметров модели. В начале каждого шага осуществляется
    проверка наличия новых данных. В случае их появления счетчик шага сбрасывается и начинается
    очередной этап с новыми данными.

    Шаг состоит из:
    - проверки наличия свободного места в популяции — создается и оценивается ребенок
    - проверка возможности достоверно оценить преимущество родителя над жертвой — жертва уничтожается
    или родитель или жертва направляются на дополнительную оценку

    Шаг прерывается после первой оценки организма.

    Организмы могут погибнуть вне очереди, если во время его оценки произошло ошибка (взрыв
    градиентов, отрицательный IR, невалидные параметры и т.д.).

    Процесс выбора организма родителя, жертвы, размножения и уничтожения регулируется функциями
    модуля популяции.
    """

    def __init__(self, max_population: int = config.MAX_POPULATION):
        """Сохраняет предельный размер популяции."""
        self._max_population = max_population
        self._end = listing.last_history_date()
        port = load_from_yaml(self._end)
        self._tickers = tuple(port.index[:-2])
        self._scale = 1.0

    def evolve(self) -> None:
        """Осуществляет эволюции.

        При необходимости создается начальная популяция из организмов по умолчанию.
        """
        self._setup()

        step = 0
        while True:  # noqa: WPS457

            if (new_end := listing.last_history_date()) != self._end:
                self._end = new_end
                self._scale = 1.0
                step = 0

            step += 1
            date = self._end.date()
            print(f"***{date}: Шаг эволюции — {step}***")  # noqa: WPS421
            population.print_stat()
            print(f"Фактор - {self._scale:.2%}\n")  # noqa: WPS421

            parent = population.get_parent()
            if self._child_produced(parent):
                continue

            prey = population.get_prey()
            if self._prey_killed(parent, prey):
                continue

            self._eval_organism("Родитель", parent)

    def _setup(self) -> None:
        """Создает популяцию из организмов по умолчанию, если организмов меньше 4."""
        count = population.count()
        print(f"Имеется {count} организмов из {self._max_population}")  # noqa: WPS421
        print()  # noqa: WPS421

        if count < 4:
            n_to_create = self._max_population - count
            for n_org in range(1, n_to_create + 1):
                print(  # noqa: WPS421
                    f"Создаю базовые генотипы — {n_org}/{n_to_create}",
                )
                organism = population.create_new_organism()
                print(organism, end="\n\n")  # noqa: WPS421

    def _child_produced(self, parent: population.Organism) -> bool:
        """Создает потомка, если есть свободное место в популяции."""
        if population.count() >= self._max_population:
            return False

        print("Родитель:")  # noqa: WPS421
        print(parent)  # noqa: WPS421
        print()  # noqa: WPS421

        child = parent.make_child(self._scale)
        self._eval_organism("Потомок", child)

        return True

    def _eval_organism(self, name: str, organism: population.Organism) -> None:
        print(f"{name} - обучается:")  # noqa: WPS421
        print(organism)  # noqa: WPS421
        print()  # noqa: WPS421

        try:
            organism.evaluate_fitness(self._tickers, self._end)
        except (ModelError, AttributeError) as error:
            organism.die()
            error = error.__class__.__name__
            print(f"Удаляю - {error}\n")  # noqa: WPS421

            self._scale *= SCALE_DOWN
            return

        if not (organism.ir > 0):  # noqa: WPS508 - защита от NaN
            organism.die()
            print(f"Удаляю - IR = {organism.ir:0.4f}\n")  # noqa: WPS421

            self._scale *= SCALE_DOWN
            return

        print(f"Timer: {organism.timer:.0f}\n")  # noqa: WPS421

    def _prey_killed(self, hunter: population.Organism, prey: population.Organism) -> bool:
        print("Родитель:")  # noqa: WPS421
        print(hunter)  # noqa: WPS421
        print()  # noqa: WPS421

        print("Добыча:")  # noqa: WPS421
        print(prey)  # noqa: WPS421
        print()  # noqa: WPS421

        if hunter.scores < 2:
            print("Недостаточно оценок...")  # noqa: WPS421
            print()  # noqa: WPS421

            return False

        print("Родитель нападает на добычу:")  # noqa: WPS421
        if prey.scores == 1:
            _, p_value = stats.ttest_1samp(
                hunter.llh,
                prey.llh[0],
                alternative="greater",
            )
        else:
            _, p_value = stats.ttest_ind(
                hunter.llh,
                prey.llh,
                permutations=np.inf,
                alternative="greater",
            )
        if p_value * (hunter.scores - 1) < config.P_VALUE:
            print(
                f"Добыча уничтожена - p_value={p_value:.2%} < {config.P_VALUE / (hunter.scores - 1):.2%}"
            )  # noqa: WPS421
            print()  # noqa: WPS421
            prey.die()

            return True

        print(
            f"Добыча выжила - p_value={p_value:.2%} > {config.P_VALUE / (hunter.scores - 1):.2%}"
        )  # noqa:
        # WPS421
        print()  # noqa: WPS421

        return False
