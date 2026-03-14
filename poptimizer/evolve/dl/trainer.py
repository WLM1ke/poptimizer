import asyncio
import collections
import itertools
import time
from typing import Literal, cast

import torch
import tqdm
from pydantic import BaseModel
from torch import optim

from poptimizer.core import consts, errors, fsm
from poptimizer.evolve.dl import builder, data_loaders, datasets, ledoit_wolf, risk
from poptimizer.evolve.dl.wave_net import backbone, wave_net
from poptimizer.evolve.evolution import evolve


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
        self._builder = builder
        self._device = _get_device()
        self._stopping = False

    async def update_model_metrics(
        self,
        ctx: fsm.Ctx,
        evolution: evolve.Evolution,
        model: evolve.Model,
    ) -> evolve.TestResults | None:
        prefix = ""
        if model.day != evolution.day:
            prefix = "outdated "

        if not model.mean:
            prefix = "new "

        ctx.info(
            "Day %s step %d models %d delta radius %.2f - %s%s",
            evolution.day,
            evolution.step,
            await ctx.count_models(),
            evolution.radius,
            prefix,
            model,
        )

        evolution.step += 1
        model.day = evolution.day

        retry = True

        while retry:
            try:
                return await self._evaluate_in_thread(ctx, evolution, model)
            except* errors.POError as err:
                root_error = errors.get_root_poptimizer_error(err)
                if not self._retry_root_error(ctx, evolution, root_error):
                    ctx.info(f"{model} deleted with {root_error!r}")
                    retry = False

        return None

    def _retry_root_error(
        self,
        ctx: fsm.Ctx,
        evolution: evolve.Evolution,
        err: errors.POError,
    ) -> bool:
        if not isinstance(err, errors.TooShortHistoryError):
            return False

        evolution.minimal_returns_days += 1
        ctx.warning("Minimal return days increased - %d", evolution.minimal_returns_days)

        if evolution.test_days == 1:
            return False

        evolution.test_days = 1
        ctx.warning("Test days reset - %d", evolution.test_days)

        return True

    async def _evaluate_in_thread(
        self,
        ctx: fsm.Ctx,
        evolution: evolve.Evolution,
        model: evolve.Model,
    ) -> evolve.TestResults:
        cfg = Cfg.model_validate(model.phenotype)
        days = datasets.Days(
            history=cfg.batch.history_days,
            forecast=evolution.forecast_days,
            test=evolution.test_days,
        )

        data, emb_size, emb_seq_size = await self._builder.build(
            ctx,
            evolution.day,
            evolution.tickers,
            days,
            cfg.batch,
        )

        try:
            return await asyncio.to_thread(
                self._evaluate,
                ctx,
                model,
                data,
                emb_size,
                emb_seq_size,
                cfg,
                evolution.forecast_days,
            )
        except asyncio.CancelledError:
            self._stopping = True

            raise

    def _evaluate(  # noqa: PLR0913
        self,
        ctx: fsm.Ctx,
        model: evolve.Model,
        data: list[datasets.TickerData],
        emb_size: list[int],
        emb_seq_size: list[int],
        cfg: Cfg,
        forecast_days: int,
    ) -> evolve.TestResults:
        start = time.monotonic()

        net = self._prepare_net(cfg, emb_size, emb_seq_size)
        self._train(ctx, net, cfg.optimizer, cfg.scheduler, data, cfg.batch.size)

        test_results = self._test(ctx, net, cfg, forecast_days, data)

        model.mean, model.cov = self._forecast(net, forecast_days, data)
        model.duration = time.monotonic() - start

        return test_results

    def _train(  # noqa: PLR0913
        self,
        ctx: fsm.Ctx,
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

        self._log_net_stats(ctx, net, scheduler.epochs, len(train_dl.dataset))  # type: ignore[arg-type]

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
        ctx: fsm.Ctx,
        net: wave_net.Net,
        cfg: Cfg,
        forecast_days: int,
        data: list[datasets.TickerData],
    ) -> evolve.TestResults:
        with torch.inference_mode():
            net.eval()

            alfa: list[float] = []
            llh: list[float] = []
            ret = 0

            for batch in data_loaders.test(data):
                if self._stopping:
                    break

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
                    cfg.risk,
                    forecast_days,
                )

                ctx.info("%s / LLH = %7.4f", rez, loss)

                alfa.append(rez.ret - rez.avr)
                llh.append(loss)
                ret += rez.ret

        return evolve.TestResults(alfa=alfa, llh=llh, ret=ret / len(alfa))

    def _forecast(
        self,
        net: wave_net.Net,
        forecast_days: int,
        data: list[datasets.TickerData],
    ) -> tuple[list[list[float]], list[list[float]]]:
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

        return cast("list[list[float]]", mean.tolist()), cov.tolist()

    def _log_net_stats(self, ctx: fsm.Ctx, net: wave_net.Net, epochs: float, steps_per_epoch: int) -> None:
        ctx.info("Epochs - %.2f / Train size - %s", epochs, steps_per_epoch)

        modules = sum(1 for _ in net.modules())
        model_params = sum(tensor.numel() for tensor in net.parameters())
        ctx.info("Layers / parameters - %d / %d", modules, model_params)

    def _prepare_net(self, cfg: Cfg, emb_size: list[int], emb_seq_size: list[int]) -> wave_net.Net:
        return wave_net.Net(
            cfg=cfg.net,
            history_days=cfg.batch.history_days,
            num_feat_count=cfg.batch.num_feat_count,
            emb_size=emb_size,
            emb_seq_size=emb_seq_size,
        ).to(self._device)
