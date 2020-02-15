"""Базовая LSTM-модель"""
from typing import Dict

import torch
from torch import nn
from torch.nn import functional


class Conv(nn.Module):
    """LSTM модель.

    Использует в качестве признаков котировки и дивиденды.
    """

    def __init__(self, channels: int = 32) -> None:
        super().__init__()
        self.channels = channels
        self.bn = nn.BatchNorm1d(2)
        self.conv1 = nn.Conv1d(2, channels, 2, 2)
        self.conv2 = nn.Conv1d(channels, channels, 2, 2)
        self.conv3 = nn.Conv1d(channels, channels, 2, 2)
        self.conv4 = nn.Conv1d(channels, channels, 2, 2)
        self.conv5 = nn.Conv1d(channels, channels, 2, 2)
        self.conv6 = nn.Conv1d(channels, channels, 2, 2)
        self.pool = nn.AdaptiveAvgPool1d(1)

        self.dense_out = nn.Linear(channels, 1)

    def forward(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Несколько LSTM слоев и выход в виде одного значения."""
        x = torch.stack([batch["Prices"], batch["Dividends"]], dim=1)
        y = self.bn(x)
        y = self.conv1(y)
        y = functional.relu(y)
        y = self.conv2(y)
        y = functional.relu(y)
        y = self.conv3(y)
        y = functional.relu(y)
        y = self.conv4(y)
        y = functional.relu(y)
        y = self.conv5(y)
        y = functional.relu(y)
        y = self.conv6(y)
        y = functional.relu(y)
        y = self.pool(y)

        return self.dense_out(y.squeeze(dim=-1))
