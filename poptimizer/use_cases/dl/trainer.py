import asyncio
import collections
import io
import itertools
import logging
from typing import Literal

import pandas as pd
import torch
import tqdm
from pydantic import BaseModel
from torch import optim

from poptimizer.domain.dl import data_loaders, datasets, risk
from poptimizer.domain.dl.wave_net import backbone, wave_net
from poptimizer.use_cases.dl import builder


class Batch(BaseModel):
    size: int
    feats: builder.Features
    days: datasets.Days

    @property
    def num_feat_count(self) -> int:
        return self.feats.close + self.feats.div + self.feats.ret

    @property
    def history_days(self) -> int:
        return self.days.history

    @property
    def forecast_days(self) -> int:
        return self.days.forecast


class Optimizer(BaseModel): ...


class Scheduler(BaseModel):
    epochs: float
    max_lr: float = 1e-3


class Cfg(BaseModel):
    batch: Batch
    net: backbone.Cfg
    optimizer: Optimizer
    scheduler: Scheduler
    risk: risk.Cfg


class RunningMean:
    def __init__(self, window_size: int) -> None:
        self._sum: float = 0
        self._que: collections.deque[float] = collections.deque([0], maxlen=window_size)

    def append(self, num: float) -> None:
        self._sum += num - self._que[0]
        self._que.append(num)

    def running_avg(self) -> float:
        return self._sum / len(self._que)


def _get_device() -> Literal["cpu", "cuda", "mps"]:
    if torch.cuda.is_available():
        return "cuda"

    if torch.backends.mps.is_available():
        return "mps"

    return "cpu"


class Trainer:
    def __init__(self, builder: builder.Builder) -> None:
        self._lgr = logging.getLogger()
        self._builder = builder
        self._device = _get_device()
        self._stopping = False

    async def run(
        self,
        tickers: tuple[str, ...],
        last_day: pd.Timestamp,
        test_days: int,
        cfg: Cfg,
        state: bytes | None,
    ) -> list[float]:
        data = await self._builder.build(tickers, last_day, cfg.batch.feats, cfg.batch.days, test_days)
        net = self._prepare_net(state, cfg)
        if state is None:
            try:
                await asyncio.to_thread(
                    self._train,
                    net,
                    cfg.scheduler,
                    data_loaders.train(data, cfg.batch.size),
                )
            except asyncio.CancelledError:
                self._stopping = True

                raise

        return self._test(net, cfg, data_loaders.test(data))

    def _train(
        self,
        net: wave_net.Net,
        scheduler: Scheduler,
        train_dl: data_loaders.DataLoader,
    ) -> None:
        optimizer = optim.AdamW(net.parameters())  # type: ignore[reportPrivateImportUsage]

        steps_per_epoch = len(train_dl)
        total_steps = 1 + int(steps_per_epoch * scheduler.epochs)

        sch = optim.lr_scheduler.OneCycleLR(  # type: ignore[attr-defined]
            optimizer,
            max_lr=scheduler.max_lr,
            total_steps=total_steps,
        )

        self._log_net_stats(net, scheduler.epochs, train_dl)

        avg_llh = RunningMean(steps_per_epoch)
        net.train()

        with tqdm.tqdm(
            itertools.islice(
                itertools.chain.from_iterable(itertools.repeat(train_dl)),
                total_steps,
            ),
            total=total_steps,
            desc="~~> Train",
        ) as progress_bar:
            for batch in progress_bar:
                if self._stopping:
                    return

                optimizer.zero_grad()

                loss = -net.llh(self._batch_to_device(batch))
                loss.backward()  # type: ignore[no-untyped-call]
                optimizer.step()  # type: ignore[reportUnknownMemberType]
                sch.step()

                avg_llh.append(-loss.item())
                progress_bar.set_postfix_str(f"{avg_llh.running_avg():.5f}")

    def _test(self, net: wave_net.Net, cfg: Cfg, test_dl: data_loaders.DataLoader) -> list[float]:
        with torch.no_grad():
            net.eval()

            alfas: list[float] = []

            for batch in test_dl:
                loss, mean, variance = net.loss_and_forecast_mean_and_var(self._batch_to_device(batch))
                rez = risk.optimize(
                    mean - 1,
                    variance,
                    batch[datasets.FeatTypes.LABEL1P].cpu().numpy() - 1,
                    batch[datasets.FeatTypes.RETURNS].cpu().numpy(),
                    cfg.risk,
                    cfg.batch.forecast_days,
                )

                self._lgr.info("%s / LLH = %8.5f", rez, loss)

                alfas.append(rez.ret - rez.avr)

        return alfas

    def _log_net_stats(self, net: wave_net.Net, epochs: float, train_dl: data_loaders.DataLoader) -> None:
        train_size = len(train_dl.dataset)  # type: ignore[arg-type]
        self._lgr.info("Epochs - %.2f / Train size - %s", epochs, train_size)

        modules = sum(1 for _ in net.modules())
        model_params = sum(tensor.numel() for tensor in net.parameters())
        self._lgr.info("Layers / parameters - %d / %d", modules, model_params)

    def _batch_to_device(self, batch: datasets.Batch) -> datasets.Batch:
        device_batch: datasets.Batch = {}
        for k, v in batch.items():
            device_batch[k] = v.to(self._device)

        return device_batch

    def _prepare_net(self, state: bytes | None, cfg: Cfg) -> wave_net.Net:
        net = wave_net.Net(
            cfg=cfg.net,
            num_feat_count=cfg.batch.num_feat_count,
            history_days=cfg.batch.history_days,
        ).to(self._device)

        if state is not None:
            buffer = io.BytesIO(state)
            state_dict = torch.load(buffer, map_location=self._device)  # type: ignore[no-untyped-call]
            net.load_state_dict(state_dict)

        return net
