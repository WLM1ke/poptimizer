"""Модель на основе WaveNet."""
from typing import Final

import numpy as np
import torch
from torch.distributions import Categorical, MixtureSameFamily

from poptimizer.dl import data_loader, exceptions

_EPS: Final = torch.tensor(torch.finfo().eps)


class SubBlock(torch.nn.Module):
    """Gated block with residual connection.

    Сохраняет размер 1D тензора и количество каналов в нем.
    """

    def __init__(self, rez_channels: int, inner_channels: int, kernels: int) -> None:
        """Gated block with residual connection.

        :param rez_channels:
            Количество каналов на входе и выходе блока.
        :param inner_channels:
            Количество внутренних каналов в signal и gate слоях.
        :param kernels:
            Размер сверток в signal и gate сверточных слоях.
        """
        super().__init__()
        self._signal_gate_pad = torch.nn.ConstantPad1d(
            padding=(kernels - 1, 0),
            value=0,
        )
        self._signal_conv = torch.nn.Conv1d(
            in_channels=rez_channels,
            out_channels=inner_channels,
            kernel_size=kernels,
            stride=1,
        )
        self._gate_conv = torch.nn.Conv1d(
            in_channels=rez_channels,
            out_channels=inner_channels,
            kernel_size=kernels,
            stride=1,
        )
        self._output_conv = torch.nn.Conv1d(
            in_channels=inner_channels,
            out_channels=rez_channels,
            kernel_size=1,
        )

    def forward(self, input_tensor: torch.Tensor) -> torch.Tensor:
        """Gated block with residual connection."""
        padded_input = self._signal_gate_pad(input_tensor)

        signal = torch.relu(self._signal_conv(padded_input))
        gate = torch.sigmoid(self._gate_conv(padded_input))
        gated_signal: torch.Tensor = self._output_conv(signal * gate)

        return input_tensor + gated_signal


class Block(torch.nn.Module):
    """Пропускает сигнал сквозь несколько SubBlock, уменьшает размер 1D тензора в два раза.

    Имеет два выхода:
    - Основной с уменьшенной в два раза размерностью
    - Скип для суммирования последнего значения слоя с остальными скипами
    """

    def __init__(
        self,
        sub_blocks: int,
        sub_blocks_kernels: int,
        sub_blocks_channels: int,
        rez_channels: int,
        skip_channels: int,
    ) -> None:
        """Пропускает сигнал сквозь несколько SubBlock, уменьшает размер 1D тензора в два раза.

        :param sub_blocks:
            Количество маленьких блоков в блоке.
        :param sub_blocks_kernels:
            Размер сверток внутри маленьких блоков.
        :param sub_blocks_channels:
            Количество каналов внутри маленьких блоков.
        :param rez_channels:
            Количество каналов на входе и по обходному пути маленьких блоков.
        :param skip_channels:
            Количество каналов у скипа.
        """
        super().__init__()

        self._sub_blocks = torch.nn.Sequential()
        for _ in range(sub_blocks):
            self._sub_blocks.append(
                SubBlock(
                    rez_channels=rez_channels,
                    inner_channels=sub_blocks_channels,
                    kernels=sub_blocks_kernels,
                ),
            )

        self._skip_conv = torch.nn.Conv1d(
            in_channels=rez_channels,
            out_channels=skip_channels,
            kernel_size=1,
        )
        self._dilated_pad = torch.nn.ConstantPad1d(
            padding=(1, 0),
            value=0,
        )
        self._dilated_conv = torch.nn.Conv1d(
            in_channels=rez_channels,
            out_channels=rez_channels,
            kernel_size=2,
            stride=2,
        )

    def forward(self, input_tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Возвращает сокращенный в два раза основной и скип сигнал."""
        gated = self._sub_blocks(input_tensor)

        dilated = self._dilated_conv(self._dilated_pad(gated))
        skip = self._skip_conv(gated[:, :, -1:])

        return dilated, skip


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
        history_days: int,
        start_bn: bool,
        num_feat_count: int,
        sub_blocks: int,
        sub_blocks_kernels: int,
        sub_blocks_channels: int,
        rez_channels: int,
        skip_channels: int,
        end_channels: int,
        mixture_size: int,
    ) -> None:
        """WaveNet-like сеть с возможностью параметризации параметров.

        :param history_days:
            Количество дней в истории.
        :param start_bn:
            Нужно ли производить BN для входящих численных значений.
        :param num_feat_count:
            Количество количественных признаков.
        :param sub_blocks:
            Количество маленьких блоков в блоке.
        :param sub_blocks_kernels:
            Размер сверток в signal и gate сверточных слоях.
        :param sub_blocks_channels:
            Количество каналов в signal и gate сверточных слоях маленьких блоков.
        :param rez_channels:
            Количество каналов на входе и по обходному пути маленьких блоков.
        :param skip_channels:
            Количество каналов у скипа.
        :param end_channels:
            Количество каналов, до которого сжимаются скипы перед расчетом финальных значений.
        :param mixture_size:
            Количество распределений в смеси. Для каждого распределения формируется три значения —
            логарифм веса для вероятности, прокси для центрального положения и положительное прокси
            для масштаба.
        :raises ModelError:
            При отсутствии признаков - вырожденная модель.
        """
        super().__init__()

        if num_feat_count == 0:
            raise exceptions.ModelError("no features")

        if start_bn:
            self._bn: torch.nn.BatchNorm1d | torch.nn.Identity = torch.nn.BatchNorm1d(num_feat_count)
        else:
            self._bn = torch.nn.Identity()

        self._start_conv = torch.nn.Conv1d(
            in_channels=num_feat_count,
            out_channels=rez_channels,
            kernel_size=1,
        )

        self._blocks = torch.nn.ModuleList()
        blocks = int(np.log2(history_days - 1)) + 1
        for _ in range(blocks):
            self._blocks.append(
                Block(
                    sub_blocks=sub_blocks,
                    sub_blocks_kernels=sub_blocks_kernels,
                    sub_blocks_channels=sub_blocks_channels,
                    rez_channels=rez_channels,
                    skip_channels=skip_channels,
                ),
            )

        self._final_skip_conv = torch.nn.Conv1d(
            in_channels=rez_channels,
            out_channels=skip_channels,
            kernel_size=1,
        )

        self._end_conv = torch.nn.Conv1d(
            in_channels=skip_channels,
            out_channels=end_channels,
            kernel_size=1,
        )

        self._output_conv_logit = torch.nn.Conv1d(
            in_channels=end_channels,
            out_channels=mixture_size,
            kernel_size=1,
        )
        self._output_conv_m = torch.nn.Conv1d(
            in_channels=end_channels,
            out_channels=mixture_size,
            kernel_size=1,
        )
        self._output_conv_s = torch.nn.Conv1d(
            in_channels=end_channels,
            out_channels=mixture_size,
            kernel_size=1,
        )
        self._output_soft_plus_s = torch.nn.Softplus()

    def forward(self, batch: data_loader.Case) -> MixtureSameFamily:
        """Возвращает смесь логнормальных распределений."""
        end = self._nn_body(batch)

        return self._nn_head(end)

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

    def _nn_body(self, batch: data_loader.Case) -> torch.Tensor:
        num_feat = batch[data_loader.FeatTypes.NUMERICAL]
        main_path = self._start_conv(self._bn(num_feat))

        skips = torch.tensor(0, dtype=torch.float)

        for block in self._blocks:
            main_path, skip = block(main_path)
            skips.add_(skip)

        skips.add_(self._final_skip_conv(main_path))

        return torch.relu(self._end_conv(torch.relu(skips)))

    def _nn_head(self, end: torch.Tensor) -> MixtureSameFamily:
        try:
            weights_dist = Categorical(
                logits=self._output_conv_logit(end).permute(0, 2, 1),
            )  # type: ignore[no-untyped-call]
        except ValueError as err:
            raise exceptions.ModelError("error in categorical distribution") from err

        std = self._output_soft_plus_s(self._output_conv_s(end)) + _EPS
        comp_dist = torch.distributions.LogNormal(
            loc=self._output_conv_m(end).permute((0, 2, 1)),
            scale=std.permute((0, 2, 1)),
        )  # type: ignore[no-untyped-call]

        return torch.distributions.MixtureSameFamily(
            mixture_distribution=weights_dist,
            component_distribution=comp_dist,
        )  # type: ignore[no-untyped-call]
