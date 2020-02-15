"""Базовая LSTM-модель"""
from typing import Dict

import torch
from torch import nn
from torch.nn import functional


class LSTM(nn.Module):
    """LSTM модель.

    Использует в качестве признаков котировки и дивиденды.
    """

    def __init__(
        self, num_layers: int = 2, hidden_size: int = 16, bidirectional: bool = True
    ) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.bidirectional = bidirectional
        self.lstm = nn.LSTM(
            2, hidden_size, num_layers, batch_first=True, bidirectional=bidirectional
        )
        input_size = hidden_size * (1 + bidirectional)
        self.dense1 = nn.Linear(input_size, input_size // 2)
        self.dense2 = nn.Linear(input_size // 2, input_size // 4)
        self.dense_out = nn.Linear(input_size // 4, 1)

    def forward(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Несколько LSTM слоев и выход в виде одного значения."""
        x = torch.stack([batch["price"], batch["div"]], dim=-1)
        output, _ = self.lstm(x)
        if self.bidirectional:
            y_forward = output[:, -1, : self.hidden_size]
            y_backward = output[:, -1, self.hidden_size :]
            y = torch.cat([y_forward, y_backward], dim=1)
        else:
            y = output[:, -1, :]
        y = self.dense1(y)
        y = functional.relu(y)
        y = self.dense2(y)
        y = functional.relu(y)
        return self.dense_out(y)
