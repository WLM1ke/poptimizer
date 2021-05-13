"""Тренировка модели."""
import collections
import io
import itertools
import sys
from typing import Optional

import pandas as pd
import torch
import tqdm
from torch import distributions, nn, optim

from poptimizer.config import DEVICE, YEAR_IN_TRADING_DAYS, POptimizerError
from poptimizer.dl import data_loader, models
from poptimizer.dl.features import data_params
from poptimizer.dl.forecast import Forecast

# Ограничение на максимальное снижение правдоподобия во время обучения для его прервывния
LLH_DRAW_DOWN = 1

# Максимальный размер документа в MongoDB
MAX_SIZE = 2_000_000


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


class TooLargeModelError(ModelError):
    """Слишком большая модель.

    Модель с 2 млн параметров не может быть сохранена.
    """


class DegeneratedModelError(ModelError):
    """В модели отключены все признаки."""


def log_normal_llh_mix(
    output: tuple[torch.Tensor, torch.Tensor, torch.Tensor],
    batch: dict[str, torch.Tensor],
) -> tuple[torch.Tensor, int, torch.Tensor]:
    """Minus Normal Log Likelihood and batch size."""
    logits, mean, std = output

    weights_dist = distributions.Categorical(logits=logits)
    comp_dist = distributions.LogNormal(mean, std)
    dist = distributions.MixtureSameFamily(weights_dist, comp_dist)

    llh = dist.log_prob(batch["Label"] + torch.tensor(1.0))

    return -llh.sum(), mean.shape[0], llh


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
    def llh(self) -> float:
        """Логарифм правдоподобия."""
        if self._llh is None:
            self._llh = self._eval_llh()
        return self._llh

    def prepare_model(self, loader: data_loader.DescribedDataLoader, verbose: bool = True) -> nn.Module:
        """Загрузка или обучение модели."""
        if self._model is not None:
            return self._model

        pickled_model = self._pickled_model
        if pickled_model:
            self._model = self._load_trained_model(pickled_model, loader, verbose)
        else:
            self._model = self._train_model()

        return self._model

    def _eval_llh(self) -> float:
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
        llh_all = []

        print(f"Тестовых дней: {days}")
        print(f"Тестовых примеров: {len(loader.dataset)}")
        with torch.no_grad():
            model.eval()
            bars = tqdm.tqdm(loader, file=sys.stdout, desc="~~> Test")
            for batch in bars:
                out = model(batch)
                loss, weight, llh = loss_fn(out, batch)
                llh_sum -= loss.item()
                weight_sum += weight
                llh_all.append(llh)

                bars.set_postfix_str(f"{llh_sum / weight_sum:.5f}")

        llh_all = torch.cat(llh_all)
        print(f"STD: {llh_all.std(unbiased=True).item() / len(llh_all) ** 0.5:.4f}")

        return llh_sum / weight_sum

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
        self,
        loader: data_loader.DescribedDataLoader,
        verbose: bool = True,
    ) -> nn.Module:
        """Создает модель с не обученными весами."""
        model_type = getattr(models, self._phenotype["type"])
        model = model_type(loader.history_days, loader.features_description, **self._phenotype["model"])

        if verbose:
            modules = sum(1 for _ in model.modules())
            print(f"Количество слоев - {modules}")
            model_params = sum(tensor.numel() for tensor in model.parameters())
            print(f"Количество параметров - {model_params}")
            if model_params > MAX_SIZE:
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

        print(f"Epochs - {epochs:.2f}")
        print(f"Train size - {len(loader.dataset)}")

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
        for batch in bars:
            optimizer.zero_grad()
            output = model(batch)

            loss, weight, _ = loss_fn(output, batch)

            llh_sum += -loss.item() - llh_deque[0]
            llh_deque.append(-loss.item())

            weight_sum += weight - weight_deque[0]
            weight_deque.append(weight)

            loss.backward()
            optimizer.step()
            scheduler.step()

            llh = llh_sum / weight_sum
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

        model = self.prepare_model(loader, verbose=False)
        model.to(DEVICE)

        means = []
        stds = []
        with torch.no_grad():
            model.eval()
            for batch in loader:
                logits, mean, std = model(batch)

                weights_dist = distributions.Categorical(logits=logits)
                comp_dist = distributions.LogNormal(mean, std)
                dist = distributions.MixtureSameFamily(weights_dist, comp_dist)

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
