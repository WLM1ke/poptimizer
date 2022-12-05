"""Основная часть сети."""
import numpy as np
import torch
from pydantic import BaseModel


class _GatedBlock(torch.nn.Module):
    """Gated block with residual connection.

    Сохраняет размер 1D тензора и количество каналов в нем.
    """

    def __init__(self, in_channels: int, inner_channels: int, kernels: int) -> None:
        super().__init__()
        self._pad = torch.nn.ConstantPad1d(
            padding=(kernels - 1, 0),
            value=0,
        )
        self._signal = torch.nn.Conv1d(
            in_channels=in_channels,
            out_channels=inner_channels,
            kernel_size=kernels,
            stride=1,
        )
        self._gate = torch.nn.Conv1d(
            in_channels=in_channels,
            out_channels=inner_channels,
            kernel_size=kernels,
            stride=1,
        )
        self._output = torch.nn.Conv1d(
            in_channels=inner_channels,
            out_channels=in_channels,
            kernel_size=1,
        )

    def forward(self, in_tensor: torch.Tensor) -> torch.Tensor:
        """Gated block with residual connection."""
        padded_input = self._pad(in_tensor)

        signal = torch.relu(self._signal(padded_input))
        gate = torch.sigmoid(self._gate(padded_input))
        gated_signal = self._output(signal * gate)

        return in_tensor + gated_signal  # type: ignore[no-any-return]


class Desc(BaseModel):
    """Описание основного части сети.

    :param blocks:
        Количество блоков.
    :param kernels:
        Размер сверток во внутренних слоях gated-блоков.
    :param channels:
        Количество каналов во внутренних слоях gated-блоков.
    :param out_channels:
        Количество каналов у скип-выхода.
    """

    blocks: int
    kernels: int
    channels: int
    out_channels: int


class _Blocks(torch.nn.Module):
    """Пропускает сигнал сквозь несколько gated-блоков, уменьшает размер 1D тензора в два раза.

    Имеет два выхода:
    - Основной выходной слой с уменьшенной в два раза размерностью
    - Скип для суммирования последнего значения слоя с остальными скипами
    """

    def __init__(self, in_channels: int, desc: Desc) -> None:
        super().__init__()

        self._blocks = torch.nn.Sequential()
        for _ in range(desc.blocks):
            self._blocks.append(
                _GatedBlock(
                    in_channels=in_channels,
                    inner_channels=desc.channels,
                    kernels=desc.kernels,
                ),
            )

        self._skip = torch.nn.Conv1d(
            in_channels=in_channels,
            out_channels=desc.out_channels,
            kernel_size=1,
        )
        self._dilated_pad = torch.nn.ConstantPad1d(
            padding=(1, 0),
            value=0,
        )
        self._dilated = torch.nn.Conv1d(
            in_channels=in_channels,
            out_channels=in_channels,
            kernel_size=2,
            stride=2,
        )

    def forward(self, in_tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Возвращает сокращенный в два раза основной и скип сигнал."""
        gated = self._blocks(in_tensor)

        dilated = self._dilated(self._dilated_pad(gated))
        skip = self._skip(gated[:, :, -1:])

        return dilated, skip


class Net(torch.nn.Module):
    """Основная часть сети.

    Состоит из нескольких блоков, каждый из которых уменьшает длину 1D тензора в два раза.
    Из последнего элемента каждого блока агрегируется выходной сигнал.
    """

    def __init__(
        self,
        history_days: int,
        in_channels: int,
        desc: Desc,
    ) -> None:
        super().__init__()

        self._blocks = torch.nn.ModuleList()
        blocks = int(np.log2(history_days - 1)) + 1

        for _ in range(blocks):
            self._blocks.append(_Blocks(in_channels=in_channels, desc=desc))

        self._final_skip_conv = torch.nn.Conv1d(
            in_channels=in_channels,
            out_channels=desc.out_channels,
            kernel_size=1,
        )

    def forward(self, in_tensor: torch.Tensor) -> torch.Tensor:
        """Возвращает смесь логнормальных распределений."""
        skips = torch.tensor(0, dtype=torch.float)

        for block in self._blocks:
            in_tensor, skip = block(in_tensor)
            skips = skips + skip

        skips.add_(self._final_skip_conv(in_tensor))

        return torch.relu(skips)
