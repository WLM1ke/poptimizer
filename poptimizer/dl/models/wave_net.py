"""Базовая LSTM-модель"""
from typing import Dict

import numpy as np
import torch
from torch import nn


class WaveNet(nn.Module):
    """Реализация WaveNet для прогнозирования котировок.

    https://arxiv.org/abs/1609.03499
    """

    def __init__(
        self,
        history_days: int,
        kernels: int = 3,
        gate_channels: int = 32,
        residual_channels: int = 32,
        skip_channels: int = 256,
        end_channels: int = 256,
    ) -> None:
        super().__init__()
        self.skip_channels = skip_channels

        # TODO: сколько признаков
        self.bn = nn.BatchNorm1d(2)

        self.start_conv = nn.Conv1d(
            in_channels=2, out_channels=residual_channels, kernel_size=1
        )

        self.dilated_pad = nn.ConstantPad1d(padding=(1, 0), value=0.0)
        self.signal_gate_pad = nn.ConstantPad1d(padding=(kernels - 1, 0), value=0.0)

        self.dilated_convs = nn.ModuleList()
        self.signal_convs = nn.ModuleList()
        self.gate_convs = nn.ModuleList()
        self.residual_convs = nn.ModuleList()
        self.skip_convs = nn.ModuleList()
        layers = int(np.log2(history_days - 1)) + 1

        for i in range(layers):
            self.dilated_convs.append(
                nn.Conv1d(
                    in_channels=residual_channels,
                    out_channels=residual_channels,
                    kernel_size=2,
                    stride=2,
                )
            )
            self.signal_convs.append(
                nn.Conv1d(
                    in_channels=residual_channels,
                    out_channels=gate_channels,
                    kernel_size=kernels,
                    stride=1,
                )
            )
            self.gate_convs.append(
                nn.Conv1d(
                    in_channels=residual_channels,
                    out_channels=gate_channels,
                    kernel_size=kernels,
                    stride=1,
                )
            )
            self.residual_convs.append(
                nn.Conv1d(
                    in_channels=gate_channels,
                    out_channels=residual_channels,
                    kernel_size=1,
                )
            )
            self.skip_convs.append(
                nn.Conv1d(
                    in_channels=gate_channels, out_channels=skip_channels, kernel_size=1
                )
            )

        self.end_conv = nn.Conv1d(
            in_channels=skip_channels, out_channels=end_channels, kernel_size=1
        )

        self.output_conv = nn.Conv1d(
            in_channels=end_channels, out_channels=1, kernel_size=1
        )

    def forward(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Реализация WaveNet для прогнозирования котировок.

        https://github.com/vincentherrmann/pytorch-wavenet/blob/master/wavenet_model.py
        """
        x = torch.stack([batch["Prices"], batch["Dividends"]], dim=1)
        y = self.bn(x)
        y = self.start_conv(y)

        skips = torch.zeros((y.shape[0], self.skip_channels, 1))
        block_convs = (
            self.dilated_convs,
            self.signal_convs,
            self.gate_convs,
            self.residual_convs,
            self.skip_convs,
        )

        for dilated, signal, gate, residual, skip in zip(*block_convs):

            #            |-----------------------------------------------|      *residual*
            #            |                                               |
            #            |    |-- signal 1x1 -- relu  --|                |
            # -> dilate -|----|                         * ----|-- 1x1 -- + -->	*input*
            #                 |-- gate 1x1   -- sigma --|     |
            #                                                1x1
            #                                                 |
            # ----------------------------------------------> + ------------->	*skip*

            if y.shape[-1] % 2:
                y = self.dilated_pad(y)
            y = dilated(y)
            y_rez = y

            y = self.signal_gate_pad(y)
            y_signal = signal(y)
            y_signal = torch.relu(y_signal)
            y_gate = gate(y)
            y_gate = torch.sigmoid(y_gate)

            y = y_signal * y_gate

            y_skip = skip(y)
            skips = skips + y_skip[:, :, -1:]

            y = residual(y)
            y = y_rez + y

        y = torch.relu(skips)
        y = self.end_conv(y)
        y = torch.relu(y)
        y = self.output_conv(y)

        return y.squeeze(dim=-1)
