"""Тренировка модели."""
import sys
from typing import Tuple, Dict, Optional

import numpy as np
import pandas as pd
import torch
import tqdm
from scipy import stats
from torch import optim
from torch.optim import lr_scheduler

from poptimizer.dl import data_loader, models, data_params

# Параметры формирования примеров для обучения сетей
DATA_PARAMS = {
    "type": "WaveNet",
    "model": {
        "start_bn": True,
        "kernels": 3,
        "sub_blocks": 1,
        "gate_channels": 16,
        "residual_channels": 16,
        "skip_channels": 16,
        "end_channels": 16,
    },
    "optimizer": {"weight_decay": 0.01},
    "scheduler": {"max_lr": 0.005, "epochs": 3},
    "data": {
        "batch_size": 100,
        "history_days": 245,
        "forecast_days": 194,
        "features": {
            "Label": {"div_share": 0.9},
            "Prices": {},
            "Dividends": {},
            "Weight": {},
        },
    },
}


class Trainer:
    """Тренирует модель на основе нейронной сети."""

    def __init__(self, tickers: Tuple[str, ...], end: pd.Timestamp, params: dict):
        self._tickers = tickers
        self._params = params

        self._train = data_loader.get_data_loader(
            tickers, end, params["data"], data_params.TrainParams
        )
        self._val = data_loader.get_data_loader(
            tickers, end, params["data"], data_params.ValParams
        )
        self._test = data_loader.get_data_loader(
            tickers, end, params["data"], data_params.TestParams
        )

        model = getattr(models, params["type"])
        self._model = model(self._train, **params["model"])

        # noinspection PyUnresolvedReferences
        self._optimizer = optim.AdamW(self._model.parameters(), **params["optimizer"])
        # noinspection PyUnresolvedReferences
        self._scheduler = lr_scheduler.OneCycleLR(
            self._optimizer, steps_per_epoch=len(self._train), **params["scheduler"]
        )

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
            r = stats.pearsonr(val_labels, val_output)[0]
            r_rang = stats.spearmanr(val_labels, val_output)[0]

            return dict(std=std, r=r, r_rang=r_rang)

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
        # noinspection PyUnresolvedReferences
        return {"t": stats.ttest_1samp(rs, 0).statistic}

    def run(self) -> dict:
        """Производит обучение и валидацию модели."""
        print(self._model)
        print(f"Количество слоев - {sum(1 for _ in self._model.modules())}")
        print(
            f"Количество параметров - {sum(tensor.numel() for tensor in self._model.parameters())}"
        )
        epochs = self._params["scheduler"]["epochs"]
        print(f"Epochs - {epochs}")
        print(f"Train size - {len(self._train.dataset)}")
        print(f"Val size - {len(self._val.dataset)}")

        stat = {}

        for epoch in range(1, epochs + 1):
            print(f"Epoch {epoch}")
            self.train_epoch()
            stat = self.val_epoch(epoch == epochs)

        stat.update(self.test_epoch())

        return stat


def main():
    """Вариант для тестирования"""
    pos = dict(
        AKRN=7 + 715 + 88 + 4,
        ALRS=2690,
        BANE=0 + 236 + 84,
        BANEP=1097 + 13 + 107 + 235,
        BSPB=4890 + 0 + 3600 + 150,
        CBOM=0 + 4400 + 71000,
        CNTLP=0 + 0 + 0 + 9000,
        CHMF=0 + 730 + 170,
        DSKY=7180 + 740 + 6380 + 4320,
        GCHE=0 + 0 + 24,
        GMKN=0 + 109 + 1,
        IRKT=0 + 3000,
        KRKNP=66 + 0 + 43,
        KZOS=1200 + 5080 + 5190,
        LSNGP=2280 + 670 + 2410,
        LSRG=0 + 649 + 0 + 80,
        MGTSP=485 + 0 + 9,
        MOEX=2110 + 200 + 290,
        MRKV=0 + 9_680_000 + 1_420_000 + 1_300_000,
        MTSS=2340 + 4520 + 480 + 520,
        MVID=0 + 0 + 800,
        NMTP=29000 + 74000 + 13000 + 67000,
        PHOR=437 + 218 + 165 + 405,
        PIKK=0 + 3090 + 0 + 90,
        PLZL=86 + 21 + 23,
        PMSBP=0 + 0 + 1160,
        PRTK=0 + 6980,
        RNFT=0 + 51 + 11,
        RTKMP=0 + 29400,
        SNGSP=45200 + 5700 + 7700 + 2000,
        TRCN=41 + 0 + 4 + 3,
        UPRO=345_000 + 451_000 + 283_000 + 85000,
        VSMO=39 + 161 + 3,
        # Бумаги с нулевым весом
        TATNP=0,
        SIBN=0,
        RTKM=0,
        UNAC=0,
        MRKC=0,
        SELG=0,
        LSNG=0,
        MSRS=0,
        SVAV=0,
        TGKA=0,
        NKNC=0,
        NVTK=0,
        LKOH=0,
        OGKB=0,
        AFLT=0,
        SNGS=0,
        MRKZ=0,
        ROSN=0,
        SBERP=0,
        VTBR=0,
        ENRU=0,
        TATN=0,
        RASP=0,
        NLMK=0,
        NKNCP=0,
        FEES=0,
        HYDR=0,
        MRKP=0,
        MTLRP=0,
        MAGN=0,
        GAZP=0,
        SBER=0,
        MGNT=0,
        RSTI=0,
        MSNG=0,
        AFKS=0,
        SFIN=0,
        TRNFP=0,
        MTLR=0,
        ISKJ=0,
        TRMK=0,
        RSTIP=0,
        OBUV=0,
        APTK=0,
        LNZL=0,
        GTRK=0,
        ROLO=0,
        FESH=0,
        IRAO=0,
        AMEZ=0,
        YAKG=0,
        AQUA=0,
        RGSS=0,
        LIFE=0,
        KBTK=0,
        KMAZ=0,
    )
    trn = Trainer(tuple(pos), pd.Timestamp("2020-03-20"), DATA_PARAMS)
    rez = trn.run()
    print(rez)


if __name__ == "__main__":
    main()
