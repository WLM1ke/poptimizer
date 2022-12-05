import collections
import io
import itertools
import logging
import sys

import torch
from pydantic import BaseModel
from torch import optim
import tqdm

from poptimizer.core import consts
from poptimizer.dl import data_loaders, datasets, utility
from poptimizer.dl.wave_net import wave_net


class Batch(BaseModel):
    """Описание батча и включенных в него признаков."""
    size: int
    feats: datasets.Features
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


class Optimizer(BaseModel):
    """Описание параметров обучения."""

class Scheduler(BaseModel):
    """Описание графика изменения параметров обучения."""
    epochs: float
    max_lr: float = 1e-3


class DLModel(BaseModel):
    batch: Batch
    net: wave_net.Desc
    optimizer: Optimizer
    scheduler: Scheduler
    utility: utility.Desc


class Trainer:
    def __init__(self, builder: datasets.Builder):
        self._logger = logging.getLogger("Trainer")
        self._builder = builder

    async def test_model(
        self,
        state: bytes | None,
        desc: DLModel,
    ):

        all_data = await self._builder.build(desc.batch.feats, desc.batch.days)
        net = _prepare_net(desc, state)

        if state is None:
            self._train(
                net,
                data_loaders.train(all_data, desc.batch.size),
                desc.scheduler,
            )

        test_dl= data_loaders.test(all_data)

        llh_sum = []

        with torch.no_grad():
            net.eval()

            for batch in test_dl:
                loss, mean, var = net.loss_and_forecast_mean_and_var(batch)
                llh_sum.append(loss)
                rez = utility.optimize(
                    mean - 1,
                    var,
                    batch[datasets.FeatTypes.LABEL1P].numpy() - 1,
                    batch[datasets.FeatTypes.RETURNS].numpy(),
                    desc.utility,
                    desc.batch.forecast_days,
                )

                self._logger.info(f"{rez} / LLH = {loss:8.5f}")

    def _train(
            self,
            net,
            train_dl,
            scheduler,
    ):
        optimizer = optim.AdamW(net.parameters())

        steps_per_epoch = len(train_dl)
        total_steps = 1 + int(steps_per_epoch * scheduler.epochs)

        sch = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=scheduler.max_lr,
            total_steps=total_steps,
        )

        self._logger.info(f"Epochs - {scheduler.epochs:.2f} / Train size - {len(train_dl.dataset)}")
        modules = sum(1 for _ in net.modules())
        model_params = sum(tensor.numel() for tensor in net.parameters())
        self._logger.info(f"Layers / parameters - {modules} / {model_params}")

        llh_sum = 0
        llh_deque = collections.deque([0], maxlen=steps_per_epoch)

        train_dl = itertools.repeat(train_dl)
        train_dl = itertools.chain.from_iterable(train_dl)
        train_dl = itertools.islice(train_dl, total_steps)

        net.train()

        with tqdm.tqdm(train_dl, file=sys.stdout, total=total_steps, desc="~~> Train") as bar:
            for batch in bar:
                optimizer.zero_grad()

                loss = -net.llh(batch)
                loss.backward()
                optimizer.step()
                sch.step()

                llh_sum += -loss.item() - llh_deque[0]
                llh_deque.append(-loss.item())

                llh = llh_sum / len(llh_deque)
                bar.set_postfix_str(f"{llh:.5f}")


def _prepare_net(desc, state):
    net = wave_net.Net(
        desc=desc.net,
        num_feat_count=desc.batch.num_feat_count,
        history_days=desc.batch.history_days,
        forecast_days=desc.batch.forecast_days,
    )
    net.to(consts.DEVICE)

    if state is not None:
        buffer = io.BytesIO(state)
        state_dict = torch.load(buffer, map_location=consts.DEVICE)
        net.load_state_dict(state_dict)

    return net


