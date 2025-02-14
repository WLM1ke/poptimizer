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


class Optimizer(BaseModel):
    lr: float
    beta1: float
    beta2: float
    eps: float
    weight_decay: float
    momentum_decay: float
    decoupled_weight_decay: bool


class Scheduler(BaseModel):
    max_lr: float
    epochs: float
    pct_start: float
    anneal_strategy: Literal["linear", "cos"]
    cycle_momentum: bool
    base_momentum: float
    max_momentum: float
    div_factor: float
    final_div_factor: float
    three_phase: bool


class Cfg(BaseModel):
    batch: builder.Batch
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
        data, emb_size = await self._builder.build(
            ctx,
            model.day,
            model.tickers,
            days,
            cfg.batch,
        )

        try:
            await asyncio.to_thread(
                self._run,
                model,
                data,
                emb_size,
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
        emb_size: list[int],
        cfg: Cfg,
        forecast_days: int,
    ) -> None:
        net = self._prepare_net(cfg, emb_size)
        self._train(net, cfg.optimizer, cfg.scheduler, data, cfg.batch.size)

        model.alfa, model.llh = self._test(net, cfg, forecast_days, data)
        model.mean, model.cov = self._forecast(net, forecast_days, data)

    def _train(
        self,
        net: wave_net.Net,
        optimizer: Optimizer,
        scheduler: Scheduler,
        data: list[datasets.TickerData],
        batch_size: int,
    ) -> None:
        train_dl = data_loaders.train(data, batch_size)
        opt = optim.NAdam(
            net.parameters(),
            lr=optimizer.lr,
            betas=(optimizer.beta1, optimizer.beta2),
            eps=optimizer.eps,
            weight_decay=optimizer.weight_decay,
            momentum_decay=optimizer.momentum_decay,
            decoupled_weight_decay=optimizer.decoupled_weight_decay,
        )

        steps_per_epoch = len(train_dl)
        total_steps = 1 + int(steps_per_epoch * scheduler.epochs)

        sch = optim.lr_scheduler.OneCycleLR(  # type: ignore[attr-defined]
            opt,
            max_lr=scheduler.max_lr,
            total_steps=total_steps,
            pct_start=scheduler.pct_start,
            anneal_strategy=scheduler.anneal_strategy,
            cycle_momentum=scheduler.cycle_momentum,
            base_momentum=scheduler.base_momentum,
            max_momentum=scheduler.max_momentum,
            div_factor=scheduler.div_factor,
            final_div_factor=scheduler.final_div_factor,
            three_phase=scheduler.three_phase,
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

                opt.zero_grad()

                loss = -net.llh(
                    batch.num_feat.to(self._device),
                    batch.emb_feat.to(self._device),
                    batch.labels.to(self._device),
                )
                loss.backward()  # type: ignore[no-untyped-call]
                opt.step()  # type: ignore[reportUnknownMemberType]
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
                    batch.emb_feat.to(self._device),
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

                self._lgr.info("%s / LLH = %7.4f", rez, loss)

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
            mean, std = net.forecast_mean_and_std(
                batch.num_feat.to(self._device),
                batch.emb_feat.to(self._device),
            )

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

    def _prepare_net(self, cfg: Cfg, emb_size: list[int]) -> wave_net.Net:
        return wave_net.Net(
            cfg=cfg.net,
            num_feat_count=cfg.batch.num_feat_count,
            emb_size=emb_size,
            history_days=cfg.batch.history_days,
        ).to(self._device)
