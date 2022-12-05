"""Сервис для обучения и оценки моделей."""
import collections
import io
import itertools
import logging

import torch
import tqdm
from pydantic import BaseModel

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
        """Количество количественных признаков."""
        return self.feats.close + self.feats.div + self.feats.ret

    @property
    def history_days(self) -> int:
        """Количество дней истори в одном обучающем примере."""
        return self.days.history

    @property
    def forecast_days(self) -> int:
        """На какое количество дней вперед делается прогноз."""
        return self.days.forecast


class Optimizer(BaseModel):
    """Описание параметров обучения."""


class Scheduler(BaseModel):
    """Описание графика изменения параметров обучения."""

    epochs: float
    max_lr: float = 1e-3


class DLModel(BaseModel):
    """Полное описание модели и используемых данных."""

    batch: Batch
    net: wave_net.Desc
    optimizer: Optimizer
    scheduler: Scheduler
    utility: utility.Desc


class RunningMean:
    """Вычисляет среднюю в скользящем окне для передаваемых значений."""

    def __init__(self, window_size: int) -> None:
        self._sum: float = 0
        self._que: collections.deque[float] = collections.deque([0], maxlen=window_size)

    def append(self, num: float) -> None:
        """Добавляет одно значение."""
        self._sum += num - self._que[0]
        self._que.append(num)

    def running_avg(self) -> float:
        """Среднее значение в скользящем окне."""
        return self._sum / len(self._que)


class Trainer:
    """Сервис для обучения и оценки моделей."""

    def __init__(self, builder: datasets.Builder):
        self._logger = logging.getLogger("Trainer")
        self._builder = builder

    async def test_model(  # noqa: WPS210
        self,
        state: bytes | None,
        desc: DLModel,
    ) -> None:
        """Тестирует качество модели на отложенной выборке.

        При отсутствии сохраненного состояния производится обучение.
        """
        all_data = await self._builder.build(desc.batch.feats, desc.batch.days)
        net = _prepare_net(state, desc)

        if state is None:
            self._train(
                net,
                data_loaders.train(all_data, desc.batch.size),
                desc.scheduler,
            )

        test_dl = data_loaders.test(all_data)

        with torch.no_grad():
            net.eval()

            for batch in test_dl:
                loss, mean, variance = net.loss_and_forecast_mean_and_var(batch)
                rez = utility.optimize(
                    mean - 1,
                    variance,
                    batch[datasets.FeatTypes.LABEL1P].numpy() - 1,
                    batch[datasets.FeatTypes.RETURNS].numpy(),
                    desc.utility,
                    desc.batch.forecast_days,
                )

                self._logger.info(f"{rez} / LLH = {loss:8.5f}")

    def _train(  # noqa: WPS210
        self,
        net: wave_net.Net,
        train_dl: data_loaders.DataLoader,
        scheduler: Scheduler,
    ) -> None:
        optimizer = torch.optim.AdamW(net.parameters())

        steps_per_epoch = len(train_dl)
        total_steps = 1 + int(steps_per_epoch * scheduler.epochs)

        sch = torch.optim.lr_scheduler.OneCycleLR(  # type: ignore[attr-defined]
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
                optimizer.zero_grad()

                loss = -net.llh(batch)
                loss.backward()  # type: ignore[no-untyped-call]
                optimizer.step()
                sch.step()

                avg_llh.append(-loss.item())
                progress_bar.set_postfix_str(f"{avg_llh.running_avg():.5f}")

    def _log_net_stats(self, net: wave_net.Net, epochs: float, train_dl: data_loaders.DataLoader) -> None:
        train_size = len(train_dl.dataset)  # type: ignore[arg-type]
        self._logger.info(f"Epochs - {epochs:.2f} / Train size - {train_size}")

        modules = sum(1 for _ in net.modules())
        model_params = sum(tensor.numel() for tensor in net.parameters())
        self._logger.info(f"Layers / parameters - {modules} / {model_params}")


def _prepare_net(state: bytes | None, desc: DLModel) -> wave_net.Net:
    net = wave_net.Net(
        desc=desc.net,
        num_feat_count=desc.batch.num_feat_count,
        history_days=desc.batch.history_days,
        forecast_days=desc.batch.forecast_days,
    )
    net.to(consts.DEVICE)

    if state is not None:
        buffer = io.BytesIO(state)
        state_dict = torch.load(buffer, map_location=consts.DEVICE)  # type: ignore[no-untyped-call]
        net.load_state_dict(state_dict)

    return net
