"""Тренировка модели."""
import collections
import io
import itertools
import sys
from typing import Tuple, Dict, Optional, NoReturn

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


def normal_llh(
    output: Tuple[torch.Tensor, torch.Tensor], batch: Dict[str, torch.Tensor]
) -> Tuple[torch.Tensor, int]:
    """Minus Normal Log Likelihood and batch size."""
    m, s = output
    dist = torch.distributions.normal.Normal(m, s)
    llh = dist.log_prob(batch["Label"])
    return -llh.sum(), m.shape[0]


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

        self._llh = None

    def __bytes__(self) -> bytes:
        """Внутреннее состояние натренированной модели в формате pickle."""
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
        loss_fn = normal_llh

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

            # Такое условие позволяет отсеять NaN
            if not (loss_current < HIGH_SCORE):
                raise GradientsError(loss_current)

        self._validate(model)

        return model

    def _validate(self, model: nn.Module) -> NoReturn:
        """Валидация модели."""
        loader = data_loader.DescribedDataLoader(
            self._tickers, self._end, self._phenotype["data"], data_params.ValParams
        )
        if len(loader.dataset) // len(self._tickers) == 0:
            print("~~> Valid: skipped...")
            return

        loss_fn = normal_llh

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
    def llh(self) -> float:
        """Логарифм правдоподобия."""
        if self._llh is None:
            self._llh = self._eval_llh()
        return self._llh

    def _eval_llh(self) -> float:
        """Вычисляет логарифм правдоподобия.

        Прогнозы пересчитываются в дневное выражение для сопоставимости и вычисляется логарифм
        правдоподобия.
        """
        loader = data_loader.DescribedDataLoader(
            self._tickers, self._end, self._phenotype["data"], data_params.TestParams
        )

        days, rez = divmod(len(loader.dataset), len(self._tickers))
        if rez:
            raise TooLongHistoryError

        model = self._model
        forecast_days = torch.tensor(
            self._phenotype["data"]["forecast_days"], dtype=torch.float
        )

        loss_fn = normal_llh

        test_loss = 0.0
        test_weight = 0.0

        print(f"Дней для тестирования: {days}")
        with torch.no_grad():
            model.eval()
            bar = tqdm.tqdm(loader, file=sys.stdout, desc="~~> Test")
            for batch in bar:
                m, s = model(batch)
                loss, weight = loss_fn(
                    (m / forecast_days, s / forecast_days ** 0.5), batch
                )
                test_loss += loss.item()
                test_weight += weight

                bar.set_postfix_str(f"{-test_loss / test_weight:.5f}")

        return -test_loss / test_weight

    def forecast(self) -> Tuple[pd.Series, pd.Series]:
        """Прогноз годовой доходности."""
        loader = data_loader.DescribedDataLoader(
            self._tickers,
            self._end,
            self._phenotype["data"],
            data_params.ForecastParams,
        )

        model = self._model

        m_list = []
        s_list = []
        with torch.no_grad():
            model.eval()
            for batch in loader:
                m, s = model(batch)
                m_list.append(m)
                s_list.append(s)
        m_forecast = torch.cat(m_list, dim=0).numpy().flatten()
        s_forecast = torch.cat(s_list, dim=0).numpy().flatten()

        m_forecast = pd.Series(m_forecast, index=list(self._tickers))
        s_forecast = pd.Series(s_forecast, index=list(self._tickers))
        year_mul = YEAR_IN_TRADING_DAYS / self._phenotype["data"]["forecast_days"]
        return m_forecast.mul(year_mul), s_forecast.mul(year_mul ** 0.5)
