"""Модель на основе WaveNet."""
from typing import Union

import numpy as np
import torch
from torch import distributions, nn

from poptimizer.config import DEVICE, POptimizerError
from poptimizer.dl.features import FeatureType

EPS = torch.tensor(torch.finfo().eps)


class ModelError(POptimizerError):
    """Базовая ошибка модели."""


class GradientsError(ModelError):
    """Слишком большие ошибки на обучении.

    Вероятно произошел взрыв градиентов.
    """


class SubBlock(nn.Module):
    """Блок с гейтом и остаточным соединением."""

    def __init__(self, kernels: int, gate_channels: int, residual_channels: int) -> None:
        """
        :param kernels:
            Размер сверток в signal и gate сверточных слоях.
        :param gate_channels:
            Количество каналов в signal и gate сверточных слоях.
        :param residual_channels:
            Количество каналов на входе и по обходному пути.
        """
        super().__init__()
        self.signal_gate_pad = nn.ConstantPad1d(padding=(kernels - 1, 0), value=0.0)
        self.signal_conv = nn.Conv1d(
            in_channels=residual_channels,
            out_channels=gate_channels,
            kernel_size=kernels,
            stride=1,
        )
        self.gate_conv = nn.Conv1d(
            in_channels=residual_channels,
            out_channels=gate_channels,
            kernel_size=kernels,
            stride=1,
        )
        self.output_conv = nn.Conv1d(
            in_channels=gate_channels, out_channels=residual_channels, kernel_size=1
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
           |-------------------------|
           | |-signal-relu-|         |
        ->-|-|             *-output->+->
             |-gate--sigma-|
        """
        y = self.signal_gate_pad(x)

        y_signal = self.signal_conv(y)
        y_signal = torch.relu(y_signal)

        y_gate = self.gate_conv(y)
        y_gate = torch.sigmoid(y_gate)

        y = y_signal * y_gate
        y = self.output_conv(y)

        return y + x


class Block(nn.Module):
    """Блок, состоящий из нескольких маленьких блоков и последующим уменьшением размерности.

    Имеет два выхода:
    - Основной с уменьшенной в два раза размерностью;
    - Скип для суммирования последнего значения слоя с остальными скипами и расчета общего выходного
    значения.
    """

    def __init__(
        self,
        sub_blocks: int,
        kernels: int,
        gate_channels: int,
        residual_channels: int,
        skip_channels: int,
    ) -> None:
        """
        :param sub_blocks:
            Количество маленьких блоков в блоке.
        :param kernels:
            Размер сверток в signal и gate сверточных слоях.
        :param gate_channels:
            Количество каналов в signal и gate сверточных слоях маленьких блоков.
        :param residual_channels:
            Количество каналов на входе и по обходному пути маленьких блоков.
        :param skip_channels:
            Количество каналов у скипа.
        """
        super().__init__()
        self.sub_blocks = nn.ModuleList()
        for i in range(sub_blocks):
            self.sub_blocks.append(
                SubBlock(
                    kernels=kernels,
                    gate_channels=gate_channels,
                    residual_channels=residual_channels,
                )
            )
        self.skip_convs = nn.Conv1d(
            in_channels=residual_channels, out_channels=skip_channels, kernel_size=1
        )
        self.dilated_pad = nn.ConstantPad1d(padding=(1, 0), value=0.0)
        self.dilated_convs = nn.Conv1d(
            in_channels=residual_channels,
            out_channels=residual_channels,
            kernel_size=2,
            stride=2,
        )

    def forward(self, x: torch.Tensor) -> (torch.Tensor, torch.Tensor):
        """
                        |-dilated->
        ->n x SubBlock -|
                        |-skip---->
        """
        y = x
        for sub_block in self.sub_blocks:
            y = sub_block(y)

        skip = self.skip_convs(y[:, :, -1:])

        y = self.dilated_pad(y)
        y = self.dilated_convs(y)

        return y, skip


class WaveNet(nn.Module):
    """За основу взята WaveNet https://arxiv.org/abs/1609.03499

    Сверточная сеть с большим полем восприятия - удваивается при увеличении глубины на один уровень,
    что позволяет анализировать длинные последовательности котировок.

    Использует два вида входных данных:

    - Временные последовательности данных о бумагах, которые объединяются в виде отдельных, проходят
    опционально
    отключаемую BN
    - Качественные характеристики бумаг, которые проходят эмбеддинг с одинаковым выходным количеством
    каналов, суммируются и добавляются к каналам временных последовательностей.

    В результате общее количество входных каналов в сеть равно количеству временных
    последовательностей и количеству каналов эмбеддинга.
    """

    def __init__(
        self,
        history_days: int,
        features_description: dict[str, tuple[FeatureType, int]],
        start_bn: bool,
        sub_blocks: int,
        kernels: int,
        gate_channels: int,
        residual_channels: int,
        skip_channels: int,
        end_channels: int,
        mixture_size: int,
    ) -> None:
        """
        :param history_days:
            Количество дней в истории.
        :param features_description:
            Описание признаков.
        :param start_bn:
            Нужно ли производить BN для входящих численных значений.
        :param sub_blocks:
            Количество маленьких блоков в блоке.
        :param kernels:
            Размер сверток в signal и gate сверточных слоях.
        :param gate_channels:
            Количество каналов в signal и gate сверточных слоях маленьких блоков.
        :param residual_channels:
            Количество каналов на входе и по обходному пути маленьких блоков.
        :param skip_channels:
            Количество каналов у скипа.
        :param end_channels:
            Количество каналов, до которого сжимаются скипы перед расчетом финальных значений.
        :param mixture_size:
            Количество распределений в смеси. Для каждого распределения формируется три значения —
            логарифм веса для вероятности, прокси для центрального положения и положительное прокси
            для масштаба.
        """
        super().__init__()

        self._features_description = features_description

        sequence_count = 0
        self.embedding_dict = nn.ModuleDict()
        self.embedding_seq_dict = nn.ModuleDict()

        for key, (feature_type, size) in features_description.items():
            if feature_type is FeatureType.SEQUENCE:
                sequence_count += 1
            if feature_type is FeatureType.EMBEDDING_SEQUENCE:
                self.embedding_seq_dict[key] = nn.Embedding(
                    num_embeddings=size, embedding_dim=residual_channels
                )
            if feature_type is FeatureType.EMBEDDING:
                self.embedding_dict[key] = nn.Embedding(
                    num_embeddings=size, embedding_dim=residual_channels
                )

        if start_bn:
            self.bn = nn.BatchNorm1d(sequence_count)
        else:
            self.bn = nn.Identity()

        if sequence_count:
            self.start_conv = nn.Conv1d(
                in_channels=sequence_count,
                out_channels=residual_channels,
                kernel_size=1,
            )

        self.blocks = nn.ModuleList()
        blocks = int(np.log2(history_days - 1)) + 1
        for block in range(blocks):
            self.blocks.append(
                Block(
                    sub_blocks=sub_blocks,
                    kernels=kernels,
                    gate_channels=gate_channels,
                    residual_channels=residual_channels,
                    skip_channels=skip_channels,
                )
            )

        self.final_skip_conv = nn.Conv1d(
            in_channels=residual_channels, out_channels=skip_channels, kernel_size=1
        )

        self.end_conv = nn.Conv1d(in_channels=skip_channels, out_channels=end_channels, kernel_size=1)

        self.output_conv_logits = nn.Conv1d(
            in_channels=end_channels,
            out_channels=mixture_size,
            kernel_size=1,
        )
        self.output_conv_m = nn.Conv1d(
            in_channels=end_channels,
            out_channels=mixture_size,
            kernel_size=1,
        )
        self.output_conv_s = nn.Conv1d(
            in_channels=end_channels,
            out_channels=mixture_size,
            kernel_size=1,
        )
        self.output_softplus_s = nn.Softplus()

    def forward(
        self, batch: dict[str, Union[torch.Tensor, list[torch.Tensor]]]
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        ->sequence-+
        ->........-+
        ->sequence-+-nb-+
                        +-start-Block-+-|-Block-|-...-Block-|-final_skip-|
        ->embedding-------------------+ |-skips-+-...-skips-+-skips------+-relu-end-relu-|-output_m->
        ->........------+                                                     |--------|
        ->embedding-----+                                                     |-output_s-softplus->
        """
        y = torch.zeros(1, 1, 1, dtype=torch.float, device=DEVICE)

        y_seq = []

        for key, (feature_type, _) in self._features_description.items():
            if feature_type is FeatureType.SEQUENCE:
                y_seq.append(batch[key])

        if y_seq:
            y = torch.stack(y_seq, dim=1)
            y = self.bn(y)
            y = self.start_conv(y)

        for key, (feature_type, _) in self._features_description.items():
            if feature_type is FeatureType.EMBEDDING_SEQUENCE:
                emb_seq = self.embedding_seq_dict[key](batch[key])
                emb_seq = emb_seq.permute((0, 2, 1))
                y = emb_seq + y
            if feature_type is FeatureType.EMBEDDING:
                emb = self.embedding_dict[key](batch[key])
                emb = emb.unsqueeze(2)
                y = emb + y

        skips = torch.tensor(0, dtype=torch.float)

        for block in self.blocks:
            y, skip = block(y)
            skips = skips + skip

        skip = self.final_skip_conv(y)
        skips = skip + skips

        y = torch.relu(skips)
        y = self.end_conv(y)
        y = torch.relu(y)

        logits = self.output_conv_logits(y)

        mean = self.output_conv_m(y)

        std = self.output_conv_s(y)
        std = self.output_softplus_s(std) + EPS

        return (
            logits.permute((0, 2, 1)),
            mean.permute((0, 2, 1)),
            std.permute(
                (0, 2, 1),
            ),
        )

    def dist(
        self,
        batch: dict[str, Union[torch.Tensor, list[torch.Tensor]]],
    ) -> distributions.Distribution:
        """Возвращает распределение доходности."""
        logits, mean, std = self(batch)

        try:
            weights_dist = distributions.Categorical(logits=logits)
        except ValueError as err:
            raise GradientsError(err)

        comp_dist = distributions.LogNormal(mean, std)

        return distributions.MixtureSameFamily(weights_dist, comp_dist)
