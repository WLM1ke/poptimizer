"""Тренировка модели."""
import collections
import io
import itertools
import sys
from typing import Optional

import numpy as np
import pandas as pd
import torch
import tqdm
from scipy import optimize
from torch import nn, optim

from poptimizer import config
from poptimizer.config import DEVICE, YEAR_IN_TRADING_DAYS
from poptimizer.dl import data_loader, ledoit_wolf, models
from poptimizer.dl.features import data_params
from poptimizer.dl.forecast import Forecast
from poptimizer.dl.models.wave_net import GradientsError, ModelError


# Ограничение на максимальное снижение правдоподобия во время обучения для его прерывания
LLH_DRAW_DOWN = 1

# Максимальный размер документа в MongoDB
MAX_SIZE = 2 * (2 ** 10) ** 2


class TooLongHistoryError(ModelError):
    """Слишком длинная история признаков.

    Отсутствуют история для всех тикеров - нужно сократить историю.
    """


class TooLargeModelError(ModelError):
    """Слишком большая модель.

    Модель с 2 млн параметров не может быть сохранена.
    """


class DegeneratedModelError(ModelError):
    """В модели отключены все признаки."""


def log_normal_llh_mix(
    model: nn.Module,
    batch: dict[str, torch.Tensor],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Minus Normal Log Likelihood and forecast means."""
    dist = model.dist(batch)
    llh = dist.log_prob(batch["Label"] + torch.tensor(1.0))

    return -llh.sum(), dist.mean - torch.tensor(1.0), dist.variance


class Model:
    """Тренирует, тестирует и прогнозирует модель на основе нейронной сети."""

    def __init__(
        self,
        tickers: tuple[str, ...],
        end: pd.Timestamp,
        phenotype: data_loader.PhenotypeData,
        pickled_model: Optional[bytes] = None,
    ):
        """Сохраняет необходимые данные.

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
            return b""

        buffer = io.BytesIO()
        state_dict = self._model.state_dict()
        torch.save(state_dict, buffer)
        return buffer.getvalue()

    @property
    def quality_metrics(self) -> tuple[float, float]:
        """Логарифм правдоподобия."""
        if self._llh is None:
            self._llh = self._eval_llh()
        return self._llh

    def prepare_model(self, loader: data_loader.DescribedDataLoader) -> nn.Module:
        """Загрузка или обучение модели."""
        if self._model is not None:
            return self._model

        pickled_model = self._pickled_model
        if pickled_model:
            self._model = self._load_trained_model(pickled_model, loader)
        else:
            self._model = self._train_model()

        return self._model

    def _eval_llh(self) -> tuple[float, float]:
        """Вычисляет логарифм правдоподобия.

        Прогнозы пересчитываются в дневное выражение для сопоставимости и вычисляется логарифм
        правдоподобия. Модель загружается при наличии сохраненных весов или обучается с нуля.
        """
        loader = data_loader.DescribedDataLoader(
            self._tickers,
            self._end,
            self._phenotype["data"],
            data_params.TestParams,
        )

        n_tickers = len(self._tickers)
        days, rez = divmod(len(loader.dataset), n_tickers)
        if rez:
            raise TooLongHistoryError

        model = self.prepare_model(loader)
        model.to(DEVICE)
        loss_fn = log_normal_llh_mix

        llh_sum = 0
        weight_sum = 0
        all_means = []
        all_vars = []
        all_labels = []

        llh_adj = np.log(data_params.FORECAST_DAYS) / 2
        with torch.no_grad():
            model.eval()
            bars = tqdm.tqdm(loader, file=sys.stdout, desc="~~> Test")
            for batch in bars:
                loss, mean, var = loss_fn(model, batch)
                llh_sum -= loss.item()
                weight_sum += mean.shape[0]
                all_means.append(mean)
                all_vars.append(var)
                all_labels.append(batch["Label"])

                bars.set_postfix_str(f"{llh_sum / weight_sum + llh_adj:.5f}")

        all_means = torch.cat(all_means).cpu().numpy().flatten()
        all_vars = torch.cat(all_vars).cpu().numpy().flatten()
        all_labels = torch.cat(all_labels).cpu().numpy().flatten()
        llh = llh_sum / weight_sum + llh_adj

        ir = _opt_port(all_means, all_vars, all_labels, self._tickers, self._end, loader.history_days)

        return llh, ir

    def _load_trained_model(
        self,
        pickled_model: bytes,
        loader: data_loader.DescribedDataLoader,
    ) -> nn.Module:
        """Создание тренированной модели."""
        model = self._make_untrained_model(loader)
        buffer = io.BytesIO(pickled_model)
        state_dict = torch.load(buffer)
        model.load_state_dict(state_dict)
        return model

    def _make_untrained_model(
        self,
        loader: data_loader.DescribedDataLoader,
    ) -> nn.Module:
        """Создает модель с не обученными весами."""
        model_type = getattr(models, self._phenotype["type"])
        model = model_type(loader.history_days, loader.features_description, **self._phenotype["model"])

        if sum(tensor.numel() for tensor in model.parameters()) > MAX_SIZE:
            raise TooLargeModelError()

        return model

    def _train_model(self) -> nn.Module:
        """Тренировка модели."""
        phenotype = self._phenotype

        loader = data_loader.DescribedDataLoader(
            self._tickers,
            self._end,
            phenotype["data"],
            data_params.TrainParams,
        )

        if len(loader.features_description) == 1:
            raise DegeneratedModelError()

        model = self._make_untrained_model(loader)
        model.to(DEVICE)
        optimizer = optim.AdamW(model.parameters(), **phenotype["optimizer"])

        steps_per_epoch = len(loader)
        scheduler_params = dict(phenotype["scheduler"])
        epochs = scheduler_params.pop("epochs")
        total_steps = 1 + int(steps_per_epoch * epochs)
        scheduler_params["total_steps"] = total_steps
        scheduler = optim.lr_scheduler.OneCycleLR(optimizer, **scheduler_params)

        print(f"Epochs - {epochs:.2f} / Train size - {len(loader.dataset)}")
        modules = sum(1 for _ in model.modules())
        model_params = sum(tensor.numel() for tensor in model.parameters())
        print(f"Количество слоев / параметров - {modules}/{model_params}")

        llh_sum = 0
        llh_deque = collections.deque([0], maxlen=steps_per_epoch)
        weight_sum = 0
        weight_deque = collections.deque([0], maxlen=steps_per_epoch)
        loss_fn = log_normal_llh_mix

        loader = itertools.repeat(loader)
        loader = itertools.chain.from_iterable(loader)
        loader = itertools.islice(loader, total_steps)

        model.train()
        bars = tqdm.tqdm(loader, file=sys.stdout, total=total_steps, desc="~~> Train")
        llh_min = None
        llh_adj = np.log(data_params.FORECAST_DAYS) / 2
        for batch in bars:
            optimizer.zero_grad()

            loss, means, _ = loss_fn(model, batch)

            llh_sum += -loss.item() - llh_deque[0]
            llh_deque.append(-loss.item())

            weight_sum += means.shape[0] - weight_deque[0]
            weight_deque.append(means.shape[0])

            loss.backward()
            optimizer.step()
            scheduler.step()

            llh = llh_sum / weight_sum + llh_adj
            bars.set_postfix_str(f"{llh:.5f}")

            if llh_min is None:
                llh_min = llh - LLH_DRAW_DOWN
            # Такое условие позволяет отсеять NaN
            if not (llh > llh_min):
                raise GradientsError(llh)

        return model

    def forecast(self) -> Forecast:
        """Прогноз годовой доходности."""
        loader = data_loader.DescribedDataLoader(
            self._tickers,
            self._end,
            self._phenotype["data"],
            data_params.ForecastParams,
        )

        model = self.prepare_model(loader)
        model.to(DEVICE)

        means = []
        stds = []
        with torch.no_grad():
            model.eval()
            for batch in loader:
                dist = model.dist(batch)

                means.append(dist.mean - torch.tensor(1.0))
                stds.append(dist.variance ** 0.5)

        means = torch.cat(means, dim=0).cpu().numpy().flatten()
        stds = torch.cat(stds, dim=0).cpu().numpy().flatten()

        means = pd.Series(means, index=list(self._tickers))
        means = means.mul(YEAR_IN_TRADING_DAYS / data_params.FORECAST_DAYS)

        stds = pd.Series(stds, index=list(self._tickers))
        stds = stds.mul((YEAR_IN_TRADING_DAYS / data_params.FORECAST_DAYS) ** 0.5)

        return Forecast(
            tickers=self._tickers,
            date=self._end,
            history_days=self._phenotype["data"]["history_days"],
            mean=means,
            std=stds,
        )


def _opt_port(
    mean: np.array,
    var: np.array,
    labels: np.array,
    tickers: tuple[str],
    end: pd.Timestamp,
    history_days: int,
) -> float:
    """Доходность портфеля с максимальными ожидаемыми темпами роста.

    Рассчитывается доходность оптимального по темпам роста портфеля в годовом выражении (RET) и
    выводится дополнительная статистика:

    - MEAN - доходность равновзвешенного портфеля в качестве простого бенчмарка
    - PLAN - ожидавшаяся доходность. Большие по модулю значения потенциально говорят о не адекватности
    модели
    - STD - ожидавшееся СКО. Большие по значения потенциально говорят о не адекватности модели
    - DD - грубая оценка ожидаемой просадки
    - POS - количество не нулевых позиций. Малое количество говорит о слабой диверсификации портфеля
    - MAX - максимальный вес актива. Большое значение говорит о слабой диверсификации портфеля
    """
    mean *= YEAR_IN_TRADING_DAYS / data_params.FORECAST_DAYS
    var *= YEAR_IN_TRADING_DAYS / data_params.FORECAST_DAYS
    labels *= YEAR_IN_TRADING_DAYS / data_params.FORECAST_DAYS

    w, sigma = _opt_weight(mean, var, tickers, end, history_days)
    ret = (w * labels).sum()
    ret_plan = (w * mean).sum()
    std_plan = (w.reshape(1, -1) @ sigma @ w.reshape(-1, 1)).item() ** 0.5
    dd = std_plan ** 2 / ret_plan

    print(
        f"RET = {ret:.2%}",
        f"MEAN = {labels.mean():.2%}",
        f"PLAN = {ret_plan:.2%}",
        f"STD = {std_plan:.2%}",
        f"DD = {dd:.2%}",
        f"POS = {(w > 0).sum()}",
        f"MAX = {w.max():.2%}",
        sep=" / ",
    )

    return ret


def _opt_weight(
    mean: np.array,
    variance: np.array,
    tickers: tuple[str],
    end: pd.Timestamp,
    history_days: int,
) -> tuple[np.array, np.array]:
    """Веса портфеля с максимальными темпами роста и использовавшаяся ковариационная матрица..

    Задача максимизации темпов роста портфеля сводится к максимизации математического ожидания
    логарифма доходности. Дополнительно накладывается ограничение на полною отсутствие кэша и
    неотрицательные веса отдельных активов.
    """
    mean = mean.reshape(-1, 1)

    sigma, *_ = ledoit_wolf.ledoit_wolf_cor(tickers, end, history_days, config.FORECAST_DAYS)
    std = variance ** 0.5
    sigma = std.reshape(1, -1) * sigma * std.reshape(-1, 1)

    w = np.ones_like(mean).flatten()

    rez = optimize.minimize(
        _expected_ln_return,
        w,
        (mean, sigma),
        bounds=[(0, None) for _ in w],
    )

    return rez.x / rez.x.sum(), sigma


def _expected_ln_return(w: np.array, mean: np.array, sigma: np.array) -> np.array:
    """Приблизительное значение минус логарифма доходности.

    Математическое ожидание логарифма доходности можно приблизить с помощью разложения Тейлора,
    как математическое ожидание доходности минус половина дисперсии. Входящие веса нормируются на
    сумму, чтобы гарантировать отсутствие кэша в портфеле.

    Для целей дальнейшего использование возвращается мис указанная величина.
    """
    w = w.reshape(-1, 1) / w.sum()

    return ((w.T @ sigma @ w) / 2 - w.T @ mean).item()
