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
from poptimizer.dl.forecast import Forecast

# Ограничение на минимальный размер правдоподобия
LOW_LLH = -100


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
            Сохраненные параметры для натренированной модели.
        """
        self._tickers = tickers
        self._end = end
        self._phenotype = phenotype
        self._pickled_model = pickled_model

        self._model = None
        self._llh = None

    def __bytes__(self) -> bytes:
        """Сохраненные параметры для натренированной модели."""
        if self._pickled_model is not None:
            return self._pickled_model

        if self._model is None:
            return bytes()

        buffer = io.BytesIO()
        state_dict = self._model.state_dict()
        torch.save(state_dict, buffer)
        return buffer.getvalue()

    @property
    def llh(self) -> float:
        """Логарифм правдоподобия."""
        if self._llh is None:
            self._llh = self._eval_llh()
        return self._llh

    def _eval_llh(self) -> float:
        """Вычисляет логарифм правдоподобия.

        Прогнозы пересчитываются в дневное выражение для сопоставимости и вычисляется логарифм
        правдоподобия. Модель загружается при наличии сохраненных весов или обучается с нуля.
        """
        loader = data_loader.DescribedDataLoader(
            self._tickers, self._end, self._phenotype["data"], data_params.TestParams
        )

        days, rez = divmod(len(loader.dataset), len(self._tickers))
        if rez:
            raise TooLongHistoryError

        model = self.get_model(loader)

        forecast_days = torch.tensor(
            self._phenotype["data"]["forecast_days"], dtype=torch.float
        )

        loss_fn = normal_llh

        llh_sum = 0.0
        weight_sum = 0.0

        print(f"Дней для тестирования: {days}")
        with torch.no_grad():
            model.eval()
            bar = tqdm.tqdm(loader, file=sys.stdout, desc="~~> Test")
            for batch in bar:
                m, s = model(batch)
                loss, weight = loss_fn(
                    (m / forecast_days, s / forecast_days ** 0.5), batch
                )
                llh_sum -= loss.item()
                weight_sum += weight

                bar.set_postfix_str(f"{llh_sum / weight_sum:.5f}")

        return llh_sum / weight_sum

    def get_model(
        self, loader: data_loader.DescribedDataLoader, verbose: bool = True
    ) -> nn.Module:
        """Загрузка или обучение модели."""
        if self._model is not None:
            return self._model

        pickled_model = self._pickled_model
        if pickled_model:
            self._model = self._load_trained_model(pickled_model, loader, verbose)
        else:
            self._model = self._train_model()

        return self._model

    def _load_trained_model(
        self,
        pickled_model: bytes,
        loader: data_loader.DescribedDataLoader,
        verbose: bool = True,
    ) -> nn.Module:
        """Создание тренированной модели."""
        model = self._make_untrained_model(loader, verbose)
        buffer = io.BytesIO(pickled_model)
        state_dict = torch.load(buffer)
        model.load_state_dict(state_dict)
        return model

    def _make_untrained_model(
        self, loader: data_loader.DescribedDataLoader, verbose: bool = True
    ) -> nn.Module:
        """Создает модель с не обученными весами."""
        model_type = getattr(models, self._phenotype["type"])
        model = model_type(loader.features_description, **self._phenotype["model"])

        if verbose:
            modules = sum(1 for _ in model.modules())
            print(f"Количество слоев - {modules}")
            params = sum(tensor.numel() for tensor in model.parameters())
            print(f"Количество параметров - {params}")

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
        llh_sum = 0.0
        llh_deque = collections.deque([0], maxlen=len_deque)
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

            llh_sum += -loss.item() - llh_deque[0]
            llh_deque.append(-loss.item())

            weight_sum += weight - weight_deque[0]
            weight_deque.append(weight)

            loss.backward()
            optimizer.step()
            scheduler.step()

            llh = llh_sum / weight_sum
            bar.set_postfix_str(f"{llh:.5f}")

            # Такое условие позволяет отсеять NaN
            if not (llh > LOW_LLH):
                raise GradientsError(llh)

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

        llh_sum = 0.0
        weight_sum = 0.0

        print(f"Val size - {len(loader.dataset)}")
        with torch.no_grad():
            model.eval()
            bar = tqdm.tqdm(loader, file=sys.stdout, desc="~~> Valid")
            for batch in bar:
                output = model(batch)
                loss, weight = loss_fn(output, batch)
                llh_sum += -loss.item()
                weight_sum += weight

                bar.set_postfix_str(f"{llh_sum / weight_sum:.5f}")

    def forecast(self) -> Forecast:
        """Прогноз годовой доходности."""
        loader = data_loader.DescribedDataLoader(
            self._tickers,
            self._end,
            self._phenotype["data"],
            data_params.ForecastParams,
        )

        model = self.get_model(loader, False)

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

        forecast_days = self._phenotype["data"]["forecast_days"]
        history_days = self._phenotype["data"]["history_days"]

        year_mul = YEAR_IN_TRADING_DAYS / forecast_days
        m_forecast = pd.Series(m_forecast, index=list(self._tickers)).mul(year_mul)
        s_forecast = pd.Series(s_forecast, index=list(self._tickers)).mul(
            year_mul ** 0.5
        )

        return Forecast(
            tickers=self._tickers,
            date=self._end,
            history_days=history_days,
            forecast_days=forecast_days,
            mean=m_forecast,
            std=s_forecast,
        )
