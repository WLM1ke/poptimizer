"""Тренировка модели."""
import collections
import io
import itertools
import math
import sys
from typing import Tuple, Dict, Optional, NoReturn

import numpy as np
import pandas as pd
import torch
import tqdm
from torch import optim, nn
from torch.optim import lr_scheduler

from poptimizer.config import POptimizerError, YEAR_IN_TRADING_DAYS
from poptimizer.dl import data_loader, models
from poptimizer.dl.features import data_params

# Ограничение на размер ошибки обучения
HIGH_SCORE = 100

# Для численной стабильности
EPS = 1e-08

# Начальный член в LLH нормального распределения
LLH_START = torch.tensor(0.5 * math.log(2 * math.pi))


class ModelError(POptimizerError):
    """Базовая ошибка модели."""


class TooLongHistoryError(ModelError):
    """Слишком длинная история признаков.

    Отсутствуют история для всех тикеров - нужно сократить историю.
    """


class GradientsError(ModelError):
    """Слишком большие ошибки на обучении.

    Вероятно произошел взрыв градиентов.
    """


class DegeneratedForecastError(ModelError):
    """Константный прогноз."""


def incremental_return(r: np.array, r_expected: np.array, std_2: np.array) -> float:
    """Вычисляет доходность оптимального инкрементального портфеля.

    Оптимальный портфель сроится из допущения отсутствия корреляции. Размеры позиций нормируются для
    достижения фиксированного СКО портфеля.

    :param r:
        Фактическая доходность.
    :param r_expected:
        Прогнозная доходность.
    :param std_2:
        Прогнозный квадрат СКО.
    :return:
        Доходность нормированного по СКО оптимального инкрементального портфеля.
    """
    r_weighted = (r_expected / std_2).sum() / (1 / std_2).sum()
    weight = (r_expected - r_weighted) / std_2
    std_portfolio = (weight ** 2 * std_2).sum() ** 0.5
    weight = weight / (std_portfolio + EPS)
    return (r * weight).sum()


class Model:
    """Тренирует, валидирует, тестирует и прогнозирует модель на основе нейронной сети."""

    def __init__(
        self,
        tickers: Tuple[str, ...],
        end: pd.Timestamp,
        phenotype: data_loader.PhenotypeData,
        pickled_model: Optional[bytes] = None,
    ):
        """
        :param tickers:
            Набор тикеров для создания данных.
        :param end:
            Конечная дата для создания данных.
        :param phenotype:
            Параметры данных, модели, оптимизатора и политики обучения.
        :param pickled_model:
            Словарь состояния обученной модели, сохраненный в формате pickle.
        """
        self._tickers = tickers
        self._end = end
        self._phenotype = phenotype

        if pickled_model:
            self._model = self._load_trained_model(pickled_model)
        else:
            self._model = self._train_model()

        self._information_ratio = None

    def __bytes__(self) -> bytes:
        """Внутреннее состояние натренированной модели в формате pickle."""
        if self._model is None:
            return bytes()
        buffer = io.BytesIO()
        state_dict = self._model.state_dict()
        torch.save(state_dict, buffer)
        return buffer.getvalue()

    def _load_trained_model(self, pickled_model: bytes) -> nn.Module:
        """Создание тренированной модели."""
        loader = data_loader.DescribedDataLoader(
            self._tickers,
            self._end,
            self._phenotype["data"],
            data_params.ForecastParams,
        )
        model = self._make_untrained_model(loader)
        buffer = io.BytesIO(pickled_model)
        state_dict = torch.load(buffer)
        model.load_state_dict(state_dict)
        return model

    def _make_untrained_model(
        self, loader: data_loader.DescribedDataLoader
    ) -> nn.Module:
        """Создает модель с не обученными весами."""
        model_type = getattr(models, self._phenotype["type"])
        model = model_type(loader.features_description, **self._phenotype["model"])
        print(f"Количество слоев - {sum(1 for _ in model.modules())}")
        print(
            f"Количество параметров - {sum(tensor.numel() for tensor in model.parameters())}"
        )
        return model

    def _train_model(self) -> nn.Module:
        """Тренировка модели."""
        phenotype = self._phenotype

        loader = data_loader.DescribedDataLoader(
            self._tickers, self._end, phenotype["data"], data_params.TrainParams
        )

        model = self._make_untrained_model(loader)
        optimizer = optim.AdamW(model.parameters(), **phenotype["optimizer"])

        steps_per_epoch = len(loader)
        scheduler_params = dict(phenotype["scheduler"])
        epochs = scheduler_params.pop("epochs")
        total_steps = 1 + int(steps_per_epoch * epochs)
        scheduler_params["total_steps"] = total_steps
        scheduler = lr_scheduler.OneCycleLR(optimizer, **scheduler_params)

        print(f"Epochs - {epochs:.2f}")
        print(f"Train size - {len(loader.dataset)}")

        len_deque = int(total_steps ** 0.5)
        loss_sum = 0.0
        loss_deque = collections.deque([0], maxlen=len_deque)
        weight_sum = 0.0
        weight_deque = collections.deque([0], maxlen=len_deque)
        loss_fn = self._llh

        loader = itertools.repeat(loader)
        loader = itertools.chain.from_iterable(loader)
        loader = itertools.islice(loader, total_steps)

        model.train()
        bar = tqdm.tqdm(loader, file=sys.stdout, total=total_steps, desc="~~> Train")
        for batch in bar:
            optimizer.zero_grad()
            output = model(batch)

            loss, weight = loss_fn(output, batch)

            loss_sum += loss.item() - loss_deque[0]
            loss_deque.append(loss.item())

            weight_sum += weight - weight_deque[0]
            weight_deque.append(weight)

            loss.backward()
            optimizer.step()
            scheduler.step()

            loss_current = loss_sum / weight_sum
            bar.set_postfix_str(f"{loss_current:.5f}")

            if loss_current > HIGH_SCORE:
                raise GradientsError(loss_current)

        self._validate(model)

        return model

    @staticmethod
    def _llh(
        output: torch.Tensor, batch: Dict[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, int]:
        """Minus Log Likelihood."""
        m, s = output
        llh = LLH_START + torch.log(s) + 0.5 * ((batch["Label"] - m) / s) ** 2
        return llh.sum(), m.shape[0]

    def _validate(self, model: nn.Module) -> NoReturn:
        """Валидация модели."""
        loader = data_loader.DescribedDataLoader(
            self._tickers, self._end, self._phenotype["data"], data_params.ValParams
        )
        if len(loader.dataset) // len(self._tickers) == 0:
            print("~~> Valid: skipped...")
            return

        loss_fn = self._llh

        val_loss = 0.0
        val_weight = 0.0

        print(f"Val size - {len(loader.dataset)}")
        with torch.no_grad():
            model.eval()
            bar = tqdm.tqdm(loader, file=sys.stdout, desc="~~> Valid")
            for batch in bar:
                output = model(batch)
                loss, weight = loss_fn(output, batch)
                val_loss += loss.item()
                val_weight += weight

                bar.set_postfix_str(f"{val_loss / val_weight:.5f}")

    @property
    def information_ratio(self) -> float:
        """Информационный коэффициент против портфеля с равным весом активов."""
        if self._information_ratio is None:
            self._information_ratio = self._eval_ir()
        return self._information_ratio

    def _eval_ir(self) -> float:
        """Вычисляет информационный коэффициент против портфеля с равным весом активов.

        Оптимальный информационный коэффициент достигается при ставках, пропорциональные разнице между
        сигналом и его средним значением для данного периода, взвешенным обратно квадрату СКО,
        нормированной на СКО. Веса дополнительно нормируются для достижения одинакового СКО во все
        периоды.
        """
        loader = data_loader.DescribedDataLoader(
            self._tickers, self._end, self._phenotype["data"], data_params.TestParams
        )

        days, rez = divmod(len(loader.dataset), len(self._tickers))
        if rez:
            raise TooLongHistoryError

        model = self._model

        labels = []
        var = []
        forecasts = []

        print(f"Дней для тестирования: {days}")
        with torch.no_grad():
            model.eval()
            bar = tqdm.tqdm(loader, file=sys.stdout, desc="~~> Test")
            for batch in bar:
                m, s = model(batch)

                labels.append(batch["Label"])
                var.append(s ** 2)
                forecasts.append(m)

        labels = torch.cat(labels, dim=0).numpy().flatten()
        var = torch.cat(var, dim=0).numpy().flatten()
        forecasts = torch.cat(forecasts, dim=0).numpy().flatten()

        r_incremental = np.zeros(days)

        for i in range(days):
            # Срезы соответствуют разным акциям в один день
            label = labels[i::days]
            std_2 = var[i::days]
            r_expected = forecasts[i::days]

            r_incremental[i] = incremental_return(label, r_expected, std_2)

        std = r_incremental.std(ddof=1)
        if np.isclose(std, 0):
            raise DegeneratedForecastError
        mean = r_incremental.mean()

        return mean / std * YEAR_IN_TRADING_DAYS ** 0.5

    def forecast(self) -> pd.Series:
        """Прогноз годовой доходности."""
        loader = data_loader.DescribedDataLoader(
            self._tickers,
            self._end,
            self._phenotype["data"],
            data_params.ForecastParams,
        )

        model = self._model

        outputs = []
        with torch.no_grad():
            model.eval()
            for batch in loader:
                output = model(batch)
                outputs.append(output)
        forecast = torch.cat(outputs, dim=0).numpy().flatten()

        if np.isclose(forecast.std(), 0):
            raise DegeneratedForecastError

        forecast = pd.Series(forecast, index=list(self._tickers))
        year_mul = YEAR_IN_TRADING_DAYS / self._phenotype["data"]["history_days"]
        return forecast * year_mul
