"""Тренировка модели."""
import collections
import itertools
import pickle
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
HIGH_SCORE = 10

# Для численной стабильности
EPS = 1e-08


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

        self._forecast = None

        self._information_ratio = None

        self._model = None

        if pickled_model is not None:
            self._forecast = data_loader.DescribedDataLoader(
                tickers, end, phenotype["data"], data_params.ForecastParams
            )
            self._model = self._make_untrained_model(self._forecast)
            state_dict = pickle.loads(pickled_model)
            self._model.load_state_dict(state_dict)

    def _make_untrained_model(self, loader) -> nn.Module:
        """Создает модель с не обученными весами."""
        model_type = getattr(models, self._phenotype["type"])
        model = model_type(loader.features_description, **self._phenotype["model"])
        print(f"Количество слоев - {sum(1 for _ in model.modules())}")
        print(
            f"Количество параметров - {sum(tensor.numel() for tensor in model.parameters())}"
        )
        return model

    @property
    def pickled_model(self) -> Optional[bytes]:
        """Внутреннее состояние натренированной модели в формате pickle."""
        if self._model is None:
            return None
        return pickle.dumps(self._model.state_dict())

    @property
    def information_ratio(self) -> float:
        """Информационный коэффициент против портфеля с равным весом активов."""
        if self._information_ratio is None:
            self._information_ratio = self._eval_ir()
        return self._information_ratio

    def _eval_ir(self) -> float:
        """Вычисляет информационный коэффициент против портфеля с равным весом активов.

        Оптимальный информационный коэффициент достигается при ставках, пропорциональные разнице между
        сигналом и его средним значением для данного периода, нормированной на СКО сигнала для данного
        периода.
        """
        loader = data_loader.DescribedDataLoader(
            self._tickers, self._end, self._phenotype["data"], data_params.TestParams
        )

        days, rez = divmod(len(loader.dataset), len(self._tickers))
        if rez:
            raise TooLongHistoryError

        if self._model is None:
            self._train_model()
        model = self._model

        labels = []
        forecasts = []

        print(f"Дней для тестирования: {days}")
        with torch.no_grad():
            model.eval()
            bar = tqdm.tqdm(loader, file=sys.stdout, desc="~~> Test")
            for batch in bar:
                forecast = model(batch)

                labels.append(batch["Label"])
                forecasts.append(forecast)

        labels = torch.cat(labels, dim=0).numpy().flatten()
        forecasts = torch.cat(forecasts, dim=0).numpy().flatten()

        r_incremental = np.zeros(days)

        for i in range(days):
            # Срезы соответствуют разным акциям в один день
            label = labels[i::days]
            r_expected = forecasts[i::days]

            r_mean = r_expected.mean()
            r_std = r_expected.std(ddof=1)

            weights = (r_expected - r_mean) / (r_std + EPS)
            r_incremental[i] = np.cov(label, weights)[1][0]

        std = r_incremental.std(ddof=1)
        if np.isclose(std, 0):
            raise DegeneratedForecastError
        mean = r_incremental.mean()

        return mean / std * YEAR_IN_TRADING_DAYS ** 0.5

    def _train_model(self) -> NoReturn:
        """Тренировка модели."""
        phenotype = self._phenotype

        loader_train = data_loader.DescribedDataLoader(
            self._tickers, self._end, phenotype["data"], data_params.TrainParams
        )

        self._model = self._make_untrained_model(loader_train)
        model = self._model

        optimizer = optim.AdamW(model.parameters(), **phenotype["optimizer"])

        steps_per_epoch = len(loader_train)
        scheduler_params = dict(phenotype["scheduler"])
        epochs = scheduler_params.pop("epochs")
        total_steps = 1 + int(steps_per_epoch * epochs)
        scheduler_params["total_steps"] = total_steps
        scheduler = lr_scheduler.OneCycleLR(optimizer, **scheduler_params)

        print(f"Epochs - {epochs:.2f}")
        print(f"Train size - {len(loader_train.dataset)}")

        loss_sum = 0.0
        loss_deque = collections.deque([0], maxlen=(total_steps + 9) // 10)
        weight_sum = 0.0
        weight_deque = collections.deque([0], maxlen=(total_steps + 9) // 10)
        loss_fn = self._mse

        loader_train = itertools.repeat(loader_train)
        loader_train = itertools.chain.from_iterable(loader_train)
        loader_train = itertools.islice(loader_train, total_steps)

        model.train()
        bar = tqdm.tqdm(
            loader_train, file=sys.stdout, total=total_steps, desc="~~> Train"
        )
        for batch in bar:
            optimizer.zero_grad()
            output = model(batch)

            loss, weight = loss_fn(output, batch)

            loss_sum += loss.item() - loss_deque[0]
            loss_deque.append(loss.item())

            weight_sum += weight.item() - weight_deque[0]
            weight_deque.append(weight.item())

            loss.backward()
            optimizer.step()
            scheduler.step()

            loss_current = loss_sum / weight_sum
            bar.set_postfix_str(f"{loss_current:.5f}")

            if loss_current > HIGH_SCORE:
                raise GradientsError(loss_current)

        self._validate()

    @staticmethod
    def _mse(
        output: torch.Tensor, batch: Dict[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """MSE."""
        weight = torch.ones_like(batch["Weight"])
        loss = (output - batch["Label"]) ** 2 * weight
        return loss.sum(), weight.sum()

    def _validate(self) -> NoReturn:
        """Валидация модели."""
        loader_val = data_loader.DescribedDataLoader(
            self._tickers, self._end, self._phenotype["data"], data_params.ValParams
        )
        if len(loader_val.dataset) // len(self._tickers) == 0:
            print("~~> Valid: skipped...")

        model = self._model
        loss_fn = self._mse

        val_loss = 0.0
        val_weight = 0.0

        print(f"Val size - {len(loader_val.dataset)}")
        with torch.no_grad():
            model.eval()
            bar = tqdm.tqdm(loader_val, file=sys.stdout, desc="~~> Valid")
            for batch in bar:
                output = model(batch)
                loss, weight = loss_fn(output, batch)
                val_loss += loss.item()
                val_weight += weight.item()

                bar.set_postfix_str(f"{val_loss / val_weight:.5f}")
