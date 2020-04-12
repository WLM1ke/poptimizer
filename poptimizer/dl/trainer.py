"""Тренировка модели."""
import collections
import itertools
import pickle
import sys
from typing import Tuple, Dict, Optional, Union, Any, NoReturn

import numpy as np
import pandas as pd
import torch
import tqdm
from torch import optim
from torch.optim import lr_scheduler

from poptimizer.dl import data_loader, models, data_params

YEAR_IN_TRADING_DAYS = 12 * 21

HIGH_SCORE = 10

PhenotypeData = Dict[str, Union[Any, "PhenotypeType"]]


class Trainer:
    """Тренирует модель на основе нейронной сети."""

    def __init__(
        self,
        tickers: Tuple[str, ...],
        end: pd.Timestamp,
        params: dict,
        model: Optional[bytes] = None,
    ):
        self._tickers = tickers
        self._params = params

        self._test = data_loader.get_data_loader(
            tickers, end, params["data"], data_params.TestParams
        )

        model_type = getattr(models, params["type"])
        self._model = model_type(self._test, **params["model"])

        _, rez = divmod(len(self._test.dataset), len(self._tickers))
        if rez:
            print("Слишком длинные признаки и метки - сократи их длину!!!")
            self._sharpe = -np.inf
            return

        train_score = 0.0

        if model is not None:
            model = pickle.loads(model)
            self._model.load_state_dict(model)
        else:
            self._train = data_loader.get_data_loader(
                tickers, end, params["data"], data_params.TrainParams
            )
            self._val = data_loader.get_data_loader(
                tickers, end, params["data"], data_params.ValParams
            )
            if len(self._val.dataset) == 0:
                print("Слишком длинные признаки и метки - сократи их длину!!!")
                self._sharpe = -np.inf
                return

            # noinspection PyUnresolvedReferences
            self._optimizer = optim.AdamW(
                self._model.parameters(), **params["optimizer"]
            )
            # noinspection PyUnresolvedReferences
            steps_per_epoch = len(self._train)
            scheduler_params = dict(params["scheduler"])
            epochs = scheduler_params.pop("epochs")
            scheduler_params["total_steps"] = 1 + int(steps_per_epoch * epochs)

            self._scheduler = lr_scheduler.OneCycleLR(
                self._optimizer, **scheduler_params
            )
            train_score = self.run()

        if train_score < HIGH_SCORE:
            self._sharpe = self.test()
        else:
            self._sharpe = -np.inf

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
        weight = torch.ones_like(batch["Weight"])
        loss = (output - batch["Label"]) ** 2 * weight
        return loss.sum(), weight.sum()

    def train(self) -> float:
        """Тренировка одну эпоху."""
        model = self._model
        optimizer = self._optimizer
        scheduler = self._scheduler
        loss_fn = self.weighted_mse
        model.train()

        train_loss = 0.0
        loss_deque = collections.deque([0], maxlen=scheduler.total_steps // 10)
        train_weight = 0.0
        weight_deque = collections.deque([0], maxlen=scheduler.total_steps // 10)

        train_dataloader = itertools.repeat(self._train)
        train_dataloader = itertools.chain.from_iterable(train_dataloader)
        train_dataloader = zip(range(1, scheduler.total_steps + 1), train_dataloader)

        bar = tqdm.tqdm(train_dataloader, file=sys.stdout)
        bar.set_description(f"~~> Train")
        for _, batch in bar:
            optimizer.zero_grad()

            output = model(batch)
            loss, weight = loss_fn(output, batch)
            train_loss += loss.item() - loss_deque[0]
            loss_deque.append(loss.item())
            train_weight += weight.item() - weight_deque[0]
            weight_deque.append(weight.item())

            loss.backward()
            optimizer.step()
            scheduler.step()

            bar.set_postfix_str(f"{train_loss / train_weight:.5f}")
        return train_loss / train_weight

    def validate(self) -> NoReturn:
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

                bar.set_postfix_str(f"{val_loss / val_weight:.5f}")

    def test(self) -> Dict[str, float]:
        """Тестирует, вычисляя значимость доходов от предсказания.

        Если делать ставки на сигнал, пропорциональные разнице между сигналом и его матожиданием,
        то средний доход от таких ставок равен ковариации между сигналом и предсказываемой величиной.

        Каждый день мы делаем ставки на по всем имеющимся бумагам, соответственно можем получить оценки
        ковариации для отдельных дней и оценить t-статистику отличности ковариации (нашей прибыли) от
        нуля.
        """
        model = self._model

        test_labels = []
        test_std = []
        test_output = []

        with torch.no_grad():
            model.eval()
            bar = tqdm.tqdm(self._test, file=sys.stdout)
            bar.set_description(f"Test")
            for batch in bar:
                output = model(batch)

                test_labels.append(batch["Label"])
                test_std.append(batch["Weight"])
                test_output.append(output)

        test_labels = torch.cat(test_labels, dim=0).numpy().flatten()
        test_std = torch.cat(test_std, dim=0).numpy().flatten()
        test_output = torch.cat(test_output, dim=0).numpy().flatten()

        days, rez = divmod(len(test_labels), len(self._tickers))
        print(f"Дней для тестирования: {days}")

        if rez:
            print("Слишком длинные признаки и метки - сократи их длину!!!")
            return -np.inf

        rs = np.zeros(days)

        rs_b = np.zeros(days)
        for i in range(days):
            # Срезы соответствуют разным акциям в один день
            r_expected = test_output[i::days]
            std_expected = test_std[i::days]
            weights = r_expected
            weights = weights / weights.sum()
            rs[i] = (test_labels[i::days] * weights).sum()

            rs_b[i] = test_labels[i::days].mean()

        std = rs.std(ddof=1)
        if np.isclose(std, 0.0):
            sharpe = -np.inf
        else:
            sharpe = rs.mean() / rs.std(ddof=1) * YEAR_IN_TRADING_DAYS ** 0.5
            sharpe_base = rs_b.mean() / rs_b.std(ddof=1) * YEAR_IN_TRADING_DAYS ** 0.5
            print(f"База - {sharpe_base:.4f}")
        if sharpe < sharpe_base + 0.0001:
            sharpe = -np.inf

        return sharpe

    def run(self) -> float:
        """Производит обучение и валидацию модели."""
        print(f"Количество слоев - {sum(1 for _ in self._model.modules())}")
        print(
            f"Количество параметров - {sum(tensor.numel() for tensor in self._model.parameters())}"
        )
        epochs = self._params["scheduler"]["epochs"]
        print(f"Epochs - {epochs:.2f}")
        print(f"Train size - {len(self._train.dataset)}")
        print(f"Val size - {len(self._val.dataset)}")

        rez = self.train()
        self.validate()

        return rez
