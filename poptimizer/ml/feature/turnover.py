"""Факторы основанные на объеме торгов."""
import numpy as np
import pandas as pd
from hyperopt import hp

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, DaysParamsMixin


class TurnOver(DaysParamsMixin, AbstractFeature):
    """Dollar trading volume - средний оборот примерно за 12 месяцев.

    Во многих исследованиях отмечается, что малоликвидные акции имеют большую доходность.

    Для отражения этих факторов рассчитывается логарифм среднего оборота. Для отражения общерыночных
    параметров ликвидности результат может быть нормирован на совокупную ликвидность анализируемых бумаг.
    """

    def get_params_space(self) -> dict:
        """Вероятностное пространство характеризуется количеством дней и необходимостью нормировки."""
        space = super().get_params_space()
        space["normalize"] = hp.choice(f"{self.name}_normalize", [True, False])
        return space

    def get(self, params=None) -> pd.Series:
        """Логарифм среднего оборота за последние несколько дней.

        Результат может быть нормирован на общий оборот анализируемых бумаг.
        """
        params = params or self._params
        days = params["days"]
        turnover = data.turnovers(self._tickers, self._last_date)
        turnover = turnover.rolling(days).mean() + 1
        if params["normalize"]:
            turnover = turnover.div(turnover.mean(axis=1), axis=0)
        turnover = turnover.apply(np.log)
        turnover = turnover.stack()
        turnover.name = self.name
        return turnover


class TurnOverVar(DaysParamsMixin, AbstractFeature):
    """Dollar trading volume variation - отношение СКО к среднему обороту примерно за 12 месяцев.

    Во многих исследованиях отмечается, что бумаги с изменчивым объемом торгов менее привлекательны
    для инвестора и требуют дополнительной доходности.
    """

    def get(self, params=None) -> pd.Series:
        """Логарифм среднего оборота за последние несколько дней.

        Результат может быть нормирован на общий оборот анализируемых бумаг.
        """
        params = params or self._params
        days = params["days"]
        turnover = data.turnovers(self._tickers, self._last_date)
        turnover = turnover.rolling(days).std() / turnover.rolling(days).mean()
        turnover = turnover.stack()
        turnover.name = self.name
        return turnover
