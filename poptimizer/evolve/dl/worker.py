import collections
import itertools
import logging
import threading
from datetime import datetime
from typing import Literal, cast

import torch
import tqdm
from pydantic import BaseModel
from torch import optim

from poptimizer.adapters import logger
from poptimizer.core import consts, errors
from poptimizer.evolve.dl import builder, data_loaders, datasets, ledoit_wolf, risk, training
from poptimizer.evolve.dl.wave_net import backbone, wave_net
from poptimizer.evolve.models import evolve


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


def _set_tqdm_thread_lock() -> None:
    # tqdm's default write lock is a multiprocessing semaphore created at the first bar; a spawn
    # worker never shares it, and a terminated worker leaves it registered as a leaked resource.
    # `set_lock` takes an unannotated parameter upstream, hence the narrowed type ignore.
    tqdm.tqdm.set_lock(threading.RLock())  # type: ignore[reportUnknownMemberType]


def train_worker(
    job: training.TrainingJob,
    data: training.TrainingData,
) -> training.TrainingResult:
    run = _TrainingRun(
        Cfg.model_validate(job.model.phenotype),
        logger.init_worker_logger("Train"),
    )

    return run.run(job, data)


class _TrainingRun:
    def __init__(self, cfg: Cfg, log: logging.Logger) -> None:
        self._cfg = cfg
        self._log = log
        self._device = _get_device()

    def run(
        self,
        job: training.TrainingJob,
        data: training.TrainingData,
    ) -> training.TrainingResult:
        _set_tqdm_thread_lock()

        net = wave_net.Net(
            cfg=self._cfg.net,
            history_days=self._cfg.batch.history_days,
            num_feat_count=self._cfg.batch.num_feat_count,
            emb_size=data.emb_size,
            emb_seq_size=data.emb_seq_size,
        ).to(self._device)

        start = datetime.now()
        self._train(net, data.tickers_data)
        test_results = self._test(net, job.evolution.forecast_days, data.tickers_data)
        forecast = self._forecast(net, job.evolution.forecast_days, data.tickers_data)

        return training.TrainingResult(
            forecast=forecast,
            duration=(datetime.now() - start).total_seconds(),
            test=test_results,
        )

    def _train(self, net: wave_net.Net, data: list[datasets.TickerData]) -> None:
        optimizer = self._cfg.optimizer
        train_dl = data_loaders.train(data, self._cfg.batch.size)
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
        scheduler = self._cfg.scheduler
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
                opt.zero_grad()

                loss = -net.llh(
                    batch.num_feat.to(self._device),
                    batch.emb_feat.to(self._device),
                    batch.emb_seq_feat.to(self._device),
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
        forecast_days: int,
        data: list[datasets.TickerData],
    ) -> evolve.TestResults:
        with torch.inference_mode():
            net.eval()

            llh: list[float] = []
            alfa = 0
            ret = 0

            for batch in data_loaders.test(data):
                loss, mean, std = net.loss_and_forecast_mean_and_std(
                    batch.num_feat.to(self._device),
                    batch.emb_feat.to(self._device),
                    batch.emb_seq_feat.to(self._device),
                    batch.labels.to(self._device),
                )
                rez = risk.optimize(
                    mean,
                    std,
                    batch.labels.numpy() - 1,
                    batch.returns.numpy(),
                    self._cfg.risk,
                    forecast_days,
                )

                self._log.info("%s / LLH = %7.4f", rez, loss)

                llh.append(loss)
                alfa += rez.ret - rez.avr
                ret += rez.ret

        return evolve.TestResults(llh=llh, alfa=alfa / len(llh), ret=ret / len(llh))

    def _forecast(
        self,
        net: wave_net.Net,
        forecast_days: int,
        data: list[datasets.TickerData],
    ) -> training.Forecast:
        with torch.inference_mode():
            net.eval()
            forecast_dl = data_loaders.forecast(data)
            if len(forecast_dl) != 1:
                raise errors.UseCasesError("invalid forecast dataloader")

            batch = next(iter(forecast_dl))
            mean, std = net.forecast_mean_and_std(
                batch.num_feat.to(self._device),
                batch.emb_feat.to(self._device),
                batch.emb_seq_feat.to(self._device),
            )

            year_multiplier = consts.YEAR_IN_TRADING_DAYS / forecast_days
            mean *= year_multiplier
            std *= year_multiplier**0.5

            total_ret = batch.returns.numpy()
            cov = std.T * ledoit_wolf.ledoit_wolf_cor(total_ret)[0] * std

        return training.Forecast(
            mean=cast("list[list[float]]", mean.tolist()),
            cov=cov.tolist(),
        )

    def _log_net_stats(self, net: wave_net.Net, epochs: float, train_size: int) -> None:
        self._log.info("Epochs - %.2f / Train size - %s", epochs, train_size)

        modules = sum(1 for _ in net.modules())
        model_params = sum(tensor.numel() for tensor in net.parameters())
        self._log.info("Layers / parameters - %d / %d", modules, model_params)
