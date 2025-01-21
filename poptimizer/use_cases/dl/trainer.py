import asyncio
import collections
import itertools
import logging
import time
from typing import Literal, cast

import torch
import tqdm
from pydantic import BaseModel
from torch import optim

from poptimizer import consts, errors
from poptimizer.domain.dl import data_loaders, datasets, ledoit_wolf, risk
from poptimizer.domain.dl.wave_net import backbone, wave_net
from poptimizer.domain.evolve import evolve
from poptimizer.use_cases import handler
from poptimizer.use_cases.dl import builder


class Batch(BaseModel):
    size: int
    feats: builder.Features
    history_days: int

    @property
    def num_feat_count(self) -> int:
        return sum(on for _, on in self.feats)


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

    async def update_model_metrics(
        self,
        ctx: handler.Ctx,
        model: evolve.Model,
        test_days: int,
    ) -> None:
        start = time.monotonic()

        cfg = Cfg.model_validate(model.phenotype)
        days = datasets.Days(
            history=cfg.batch.history_days,
            forecast=model.forecast_days,
            test=test_days,
        )
        data = await self._builder.build(ctx, model.day, model.tickers, cfg.batch.feats, days)

        try:
            await asyncio.to_thread(
                self._run,
                model,
                data,
                cfg,
                model.forecast_days,
            )
        except asyncio.CancelledError:
            self._stopping = True

            raise

        model.risk_tolerance = cfg.risk.risk_tolerance
        model.duration = time.monotonic() - start

    def _run(
        self,
        model: evolve.Model,
        data: list[datasets.TickerData],
        cfg: Cfg,
        forecast_days: int,
    ) -> None:
        net = self._prepare_net(cfg)
        self._train(net, cfg.scheduler, data, cfg.batch.size)

        model.alfa, model.llh = self._test(net, cfg, forecast_days, data)
        model.mean, model.cov = self._forecast(net, forecast_days, data)

    def _train(
        self,
        net: wave_net.Net,
        scheduler: Scheduler,
        data: list[datasets.TickerData],
        batch_size: int,
    ) -> None:
        train_dl = data_loaders.train(data, batch_size)
        optimizer = optim.NAdam(net.parameters())  # type: ignore[reportPrivateImportUsage]

        steps_per_epoch = len(train_dl)
        total_steps = 1 + int(steps_per_epoch * scheduler.epochs)

        sch = optim.lr_scheduler.OneCycleLR(  # type: ignore[attr-defined]
            optimizer,
            max_lr=scheduler.max_lr,
            total_steps=total_steps,
        )

        self._log_net_stats(net, scheduler.epochs, len(train_dl.dataset))  # type: ignore[arg-type]

        avg_llh = RunningMean(steps_per_epoch)
        net.train()

        with tqdm.tqdm(
            itertools.islice(
                itertools.chain.from_iterable(itertools.repeat(train_dl)),
                total_steps,
            ),
            total=total_steps,
            desc="Train",
        ) as progress_bar:
            for batch in progress_bar:
                if self._stopping:
                    return

                optimizer.zero_grad()

                loss = -net.llh(
                    batch.num_feat.to(self._device),
                    batch.labels.to(self._device),
                )
                loss.backward()  # type: ignore[no-untyped-call]
                optimizer.step()  # type: ignore[reportUnknownMemberType]
                sch.step()

                avg_llh.append(-loss.item())
                progress_bar.set_postfix_str(f"{avg_llh.running_avg():.5f}")

    def _test(
        self,
        net: wave_net.Net,
        cfg: Cfg,
        forecast_days: int,
        data: list[datasets.TickerData],
    ) -> tuple[list[float], list[float]]:
        with torch.no_grad():
            net.eval()

            alfa: list[float] = []
            llh: list[float] = []

            for batch in data_loaders.test(data):
                if self._stopping:
                    break

                loss, mean, std = net.loss_and_forecast_mean_and_std(
                    batch.num_feat.to(self._device),
                    batch.labels.to(self._device),
                )
                rez = risk.optimize(
                    mean,
                    std,
                    batch.labels.numpy() - 1,
                    batch.returns.numpy(),
                    cfg.risk,
                    forecast_days,
                )

                self._lgr.info("%s / LLH = %8.5f", rez, loss)

                alfa.append(rez.ret - rez.avr)
                llh.append(loss)

        return alfa, llh

    def _forecast(
        self,
        net: wave_net.Net,
        forecast_days: int,
        data: list[datasets.TickerData],
    ) -> tuple[list[list[float]], list[list[float]]]:
        with torch.no_grad():
            net.eval()
            forecast_dl = data_loaders.forecast(data)
            if len(forecast_dl) != 1:
                raise errors.UseCasesError("invalid forecast dataloader")

            batch = next(iter(forecast_dl))
            mean, std = net.forecast_mean_and_std(batch.num_feat.to(self._device))

            year_multiplier = consts.YEAR_IN_TRADING_DAYS / forecast_days
            mean *= year_multiplier
            std *= year_multiplier**0.5

            total_ret = batch.returns.numpy()
            cov = std.T * ledoit_wolf.ledoit_wolf_cor(total_ret)[0] * std

        return cast(list[list[float]], mean.tolist()), cov.tolist()

    def _log_net_stats(self, net: wave_net.Net, epochs: float, steps_per_epoch: int) -> None:
        self._lgr.info("Epochs - %.2f / Train size - %s", epochs, steps_per_epoch)

        modules = sum(1 for _ in net.modules())
        model_params = sum(tensor.numel() for tensor in net.parameters())
        self._lgr.info("Layers / parameters - %d / %d", modules, model_params)

    def _prepare_net(self, cfg: Cfg) -> wave_net.Net:
        return wave_net.Net(
            cfg=cfg.net,
            num_feat_count=cfg.batch.num_feat_count,
            history_days=cfg.batch.history_days,
        ).to(self._device)
