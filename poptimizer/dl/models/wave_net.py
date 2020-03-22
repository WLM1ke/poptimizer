"""Базовая LSTM-модель"""
from typing import Dict, Union, List

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader


class SubBlock(nn.Module):
    """Блок с гейтами."""

    def __init__(
        self, kernels: int = 2, gate_channels: int = 32, residual_channels: int = 32
    ) -> None:
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
        self.residual_conv = nn.Conv1d(
            in_channels=gate_channels, out_channels=residual_channels, kernel_size=1
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """         |----------------------------------------------|  *residual*
                    |                                              |
                    |    |-- signal 1x1 -- relu  --|               |
           -> ------|----|                         * ------ 1x1 -- + -->
                         |-- gate 1x1   -- sigma --|
         """
        y = self.signal_gate_pad(x)
        y_signal = self.signal_conv(y)
        y_signal = torch.relu(y_signal)
        y_gate = self.gate_conv(y)
        y_gate = torch.sigmoid(y_gate)
        y = y_signal * y_gate
        y = self.residual_conv(y)
        return y + x


class Block(nn.Module):
    """Блок, состоящий из нескольких маленьких блоков скипом и уменьшением размера последовательности
    в конце."""

    def __init__(
        self,
        kernels: int = 2,
        sub_blocks: int = 2,
        gate_channels: int = 32,
        residual_channels: int = 32,
        skip_channels: int = 256,
    ) -> None:
        super().__init__()
        self.gated_sub_blocks = nn.ModuleList()
        for i in range(sub_blocks):
            self.gated_sub_blocks.append(
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
        """Большой блок."""
        y = x
        for sub_block in self.gated_sub_blocks:
            y = sub_block(y)
        skip = self.skip_convs(y)
        skip = skip[:, :, -1:]
        y = self.dilated_pad(y)
        y = self.dilated_convs(y)
        return y, skip


class WaveNet(nn.Module):
    """Реализация WaveNet для прогнозирования котировок.

    https://arxiv.org/abs/1609.03499
    """

    def __init__(
        self,
        data_loader: DataLoader,
        start_bn: bool = True,
        kernels: int = 2,
        sub_blocks: int = 2,
        gate_channels: int = 32,
        residual_channels: int = 32,
        skip_channels: int = 256,
        end_channels: int = 256,
    ) -> None:
        super().__init__()
        batch = next(iter(data_loader))
        in_sequences = len(batch["Sequence"])
        history_days = batch["Sequence"][0].shape[1]

        self.skip_channels = skip_channels
        self.bn = start_bn and nn.BatchNorm1d(in_sequences)
        self.start_conv = nn.Conv1d(
            in_channels=in_sequences, out_channels=residual_channels, kernel_size=1
        )

        self.blocks = nn.ModuleList()
        blocks = int(np.log2(history_days - 1)) + 1
        for block in range(blocks):
            self.blocks.append(
                Block(
                    kernels=kernels,
                    sub_blocks=sub_blocks,
                    gate_channels=gate_channels,
                    residual_channels=residual_channels,
                    skip_channels=skip_channels,
                )
            )
        self.final_skip_conv = nn.Conv1d(
            in_channels=residual_channels, out_channels=skip_channels, kernel_size=1
        )
        self.end_conv = nn.Conv1d(
            in_channels=skip_channels, out_channels=end_channels, kernel_size=1
        )
        self.output_conv = nn.Conv1d(
            in_channels=end_channels, out_channels=1, kernel_size=1
        )

    def forward(
        self, batch: Dict[str, Union[torch.Tensor, List[torch.Tensor]]]
    ) -> torch.Tensor:
        """Реализация WaveNet для прогнозирования котировок.

        https://github.com/vincentherrmann/pytorch-wavenet/blob/master/wavenet_model.py
        """
        y = torch.stack(batch["Sequence"], dim=1)
        if self.bn:
            y = self.bn(y)
        y = self.start_conv(y)

        skips = torch.zeros((y.shape[0], self.skip_channels, 1))

        for block in self.blocks:
            y, skip = block(y)
            skips = skips + skip

        skip = self.final_skip_conv(y)
        skips = skip + skips

        y = torch.relu(skips)
        y = self.end_conv(y)
        y = torch.relu(y)
        y = self.output_conv(y)

        return y.squeeze(dim=-1)
