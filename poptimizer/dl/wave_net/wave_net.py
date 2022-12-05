"""Сеть на основе WaveNet."""
import numpy as np
import torch
from numpy.typing import NDArray
from pydantic import BaseModel
from torch.distributions import MixtureSameFamily

from poptimizer.core import consts
from poptimizer.dl import datasets, exceptions
from poptimizer.dl.wave_net import backbone, head, inputs


class Desc(BaseModel):
    """Описание трех основных блоков сети."""

    input: inputs.Desc
    backbone: backbone.Desc
    head: head.Desc


class Net(torch.nn.Module):
    """WaveNet-like сеть с возможностью параметризации параметров.

    https://arxiv.org/abs/1609.03499

    Сверточная сеть с большим полем восприятия - удваивается при увеличении глубины на один уровень,
    что позволяет анализировать длинные последовательности котировок.

    Использует два вида входных данных:

    - Временные последовательности данных о бумагах - объединяются в виде отдельных рядов и проходят через
      опционально отключаемую BatchNorm, а потом Conv1D
    - Качественные характеристики бумаг, которые проходят Embedding с одинаковым выходным количеством
      каналов, суммируются и добавляются к каналам временных последовательностей

    Полученные данные пропускаются через WaveNet. На выходе получается ожидаемое распределение доходностей, которое
    обучается с помощью максимизации llh.
    """

    def __init__(
        self,
        desc: Desc,
        num_feat_count: int,
        history_days: int,
        forecast_days: int,
    ) -> None:
        super().__init__()

        self._forecast_days = torch.tensor(
            forecast_days,
            dtype=torch.float,
            device=consts.DEVICE,
        )
        self._llh_adj = torch.log(self._forecast_days) / 2

        self._input = inputs.Net(
            num_feat_count=num_feat_count,
            desc=desc.input,
        )
        self._backbone = backbone.Net(
            history_days=history_days,
            in_channels=desc.input.out_channels,
            desc=desc.backbone,
        )
        self._head = head.Net(
            in_channels=desc.backbone.out_channels,
            desc=desc.head,
        )

    def forward(self, batch: datasets.Batch) -> MixtureSameFamily:
        """Возвращает смесь логнормальных распределений."""
        norm_input = self._input(batch)
        end = self._backbone(norm_input)

        return self._head(end)  # type: ignore[no-any-return]

    def llh(self, batch: datasets.Batch) -> torch.Tensor:
        """Минус Log Likelihood с поправкой, обеспечивающей сопоставимость при разной длине прогноза."""
        dist = self(batch)

        labels = batch[datasets.FeatTypes.LABEL1P]

        try:
            return self._llh_adj.add(dist.log_prob(labels).mean())
        except ValueError as err:
            raise exceptions.ModelError("error in categorical distribution") from err

    def loss_and_forecast_mean_and_var(
        self,
        batch: datasets.Batch,
    ) -> tuple[float, NDArray[np.double], NDArray[np.double]]:
        """Minus Normal Log Likelihood and forecast means and vars."""
        dist = self(batch)

        labels = batch[datasets.FeatTypes.LABEL1P]

        try:
            llh = self._llh_adj.add(dist.log_prob(labels).mean())
        except ValueError as err:
            raise exceptions.ModelError("error in categorical distribution") from err

        return llh.item(), dist.mean.numpy(), dist.variance.numpy()
