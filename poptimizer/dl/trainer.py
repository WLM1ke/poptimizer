"""Тренировка модели."""
import pickle
import sys
from typing import Tuple, Dict, Optional, Union, Any

import numpy as np
import pandas as pd
import torch
import tqdm
from torch import optim
from torch.optim import lr_scheduler

from poptimizer.dl import data_loader, models, data_params

YEAR_IN_TRADING_DAYS = 12 * 21

PhenotypeType = Dict[str, Union[Any, "PhenotypeType"]]


class Trainer:
    """Тренирует модель на основе нейронной сети."""

    def __init__(
        self,
        tickers: Tuple[str, ...],
        end: pd.Timestamp,
        params: dict,
        model: Optional[bytes],
    ):
        self._tickers = tickers
        self._params = params

        self._test = data_loader.get_data_loader(
            tickers, end, params["data"], data_params.TestParams
        )

        model_type = getattr(models, params["type"])
        self._model = model_type(self._test, **params["model"])

        if model:
            model = pickle.loads(model)
            self._model.load_state_dict(model)
        else:
            self._train = data_loader.get_data_loader(
                tickers, end, params["data"], data_params.TrainParams
            )
            self._val = data_loader.get_data_loader(
                tickers, end, params["data"], data_params.ValParams
            )
            # noinspection PyUnresolvedReferences
            self._optimizer = optim.AdamW(
                self._model.parameters(), **params["optimizer"]
            )
            # noinspection PyUnresolvedReferences
            self._scheduler = lr_scheduler.OneCycleLR(
                self._optimizer, steps_per_epoch=len(self._train), **params["scheduler"]
            )
            self.train()

        self._sharpe = self.test_epoch()

    @property
    def sharpe(self):
        """Коэффициент Шарпа модели."""
        return self._sharpe

    @property
    def model(self) -> bytes:
        """Внутреннее состояние натренированной модели в формате pickle."""
        return pickle.dumps(self._model.state_dict())

    @staticmethod
    def weighted_mse(
        output: torch.Tensor, batch: Dict[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Взвешенный MSE."""
        weight = batch["Weight"]
        loss = (output - batch["Label"]) ** 2 * weight
        return loss.sum(), weight.sum()

    def train_epoch(self) -> None:
        """Тренировка одну эпоху."""
        model = self._model
        optimizer = self._optimizer
        scheduler = self._scheduler
        loss_fn = self.weighted_mse

        model.train()

        train_loss = 0.0
        train_weight = 0.0

        bar = tqdm.tqdm(self._train, file=sys.stdout)
        bar.set_description(f"~~> Train")
        for batch in bar:
            optimizer.zero_grad()

            output = model(batch)
            loss, weight = loss_fn(output, batch)
            train_loss += loss.item()
            train_weight += weight.item()

            loss.backward()
            optimizer.step()
            scheduler.step()

            bar.set_postfix_str(f"{train_loss / train_weight:.5f}")

    def val_epoch(self, get_stat: bool) -> Optional[Dict[str, float]]:
        """Валидация на одной эпохе"""
        model = self._model
        loss_fn = self.weighted_mse

        val_loss = 0.0
        val_weight = 0.0
        val_labels = []
        val_output = []

        with torch.no_grad():
            model.eval()
            bar = tqdm.tqdm(self._val, file=sys.stdout)
            bar.set_description(f"~~> Valid")
            for batch in bar:
                output = model(batch)
                loss, weight = loss_fn(output, batch)
                val_loss += loss.item()
                val_weight += weight.item()

                if get_stat:
                    val_labels.append(batch["Label"])
                    val_output.append(output)

                bar.set_postfix_str(f"{val_loss / val_weight:.5f}")

        if get_stat:
            val_loss /= val_weight
            val_labels = torch.cat(val_labels, dim=0).numpy().flatten()
            val_output = torch.cat(val_output, dim=0).numpy().flatten()

            std = val_loss ** 0.5
            # r = stats.pearsonr(val_labels, val_output)[0]
            # r_rang = stats.spearmanr(val_labels, val_output)[0]

            # return dict(std=std, r=r, r_rang=r_rang)

    def test_epoch(self) -> Dict[str, float]:
        """Тестирует, вычисляя значимость доходов от предсказания.

        Если делать ставки на сигнал, пропорциональные разнице между сигналом и его матожиданием,
        то средний доход от таких ставок равен ковариации между сигналом и предсказываемой величиной.

        Каждый день мы делаем ставки на по всем имеющимся бумагам, соответственно можем получить оценки
        ковариации для отдельных дней и оценить t-статистику отличности ковариации (нашей прибыли) от
        нуля.
        """
        model = self._model

        test_labels = []
        test_output = []

        with torch.no_grad():
            model.eval()
            bar = tqdm.tqdm(self._test, file=sys.stdout)
            bar.set_description(f"Test")
            for batch in bar:
                output = model(batch)

                test_labels.append(batch["Label"])
                test_output.append(output)

        test_labels = torch.cat(test_labels, dim=0).numpy().flatten()
        test_output = torch.cat(test_output, dim=0).numpy().flatten()

        days, rez = divmod(len(test_labels), len(self._tickers))
        print(f"Дней для тестирования: {days}")

        if rez:
            print("Слишком длинные признаки и метки - сократи их длину!!!")
            # raise POptimizerError(
            #    "Слишком длинные признаки и метки - сократи их длину!!!"
            # )

        rs = np.zeros(days)
        for i in range(days):
            # Срезы соответствуют разным акциям в один день
            rs[i] = np.cov(test_labels[i::days], test_output[i::days])[1][0]

        std = rs.std(ddof=1)
        if np.isclose(std, 0.0):
            sharpe = -np.inf
        else:
            sharpe = rs.mean() / rs.std(ddof=1) * YEAR_IN_TRADING_DAYS ** 0.5

        return sharpe

    def train(self):
        """Производит обучение и валидацию модели."""
        print(f"Количество слоев - {sum(1 for _ in self._model.modules())}")
        print(
            f"Количество параметров - {sum(tensor.numel() for tensor in self._model.parameters())}"
        )
        epochs = self._params["scheduler"]["epochs"]
        print(f"Epochs - {epochs}")
        print(f"Train size - {len(self._train.dataset)}")
        print(f"Val size - {len(self._val.dataset)}")

        for epoch in range(1, epochs + 1):
            print(f"Epoch {epoch}")
            self.train_epoch()
            self.val_epoch(epoch == epochs)
