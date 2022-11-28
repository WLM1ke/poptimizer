"""Сеть на основе WaveNet."""
import torch
from torch.distributions import MixtureSameFamily

from poptimizer.dl import data_loader, exceptions
from poptimizer.dl.wave_net import backbone, head, inputs


class WaveNet(torch.nn.Module):
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
        input_desc: inputs.Desc,
        backbone_desc: backbone.Desc,
        head_desc: head.Desc,
    ) -> None:
        super().__init__()

        self._input = inputs.Net(input_desc)
        self._backbone = backbone.Net(
            history_days=input_desc.history_days,
            in_channels=input_desc.out_channels,
            desc=backbone_desc,
        )
        self._head = head.Net(in_channels=backbone_desc.out_channels, desc=head_desc)

    def forward(self, batch: data_loader.Case) -> MixtureSameFamily:
        """Возвращает смесь логнормальных распределений."""
        norm_input = self._input(batch)
        end = self._backbone(norm_input)

        return self._head(end)  # type: ignore[no-any-return]

    def loss_and_forecast_mean_and_var(
        self,
        batch: data_loader.Case,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Minus Normal Log Likelihood and forecast means and vars."""
        dist = self(batch)

        labels = batch[data_loader.FeatTypes.LABEL1P]

        try:
            llh = dist.log_prob(labels)
        except ValueError as err:
            raise exceptions.ModelError("error in categorical distribution") from err

        llh = -llh.sum()
        mean = dist.mean - torch.tensor(1.0)

        return llh, mean, dist.variance
