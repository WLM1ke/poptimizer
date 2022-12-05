"""Голова сети."""
from typing import Final

import torch
from pydantic import BaseModel
from torch.distributions import Categorical, MixtureSameFamily

from poptimizer.dl import exceptions

_EPS: Final = torch.tensor(torch.finfo().eps)


class Desc(BaseModel):
    """Описание головы сети.

    :param channels:
        Количество каналов, до которого сжимаются входные данные перед расчетом финальных значений.
    :param mixture_size:
        Количество распределений в смеси. Для каждого распределения формируется три значения —
        логарифм веса для вероятности, прокси для центрального положения и положительное прокси
        для масштаба.
    """

    channels: int
    mixture_size: int


class Net(torch.nn.Module):
    """Голова сети - на выходе получается ожидаемое распределение доходностей."""

    def __init__(self, in_channels: int, desc: Desc) -> None:
        super().__init__()

        self._end = torch.nn.Conv1d(
            in_channels=in_channels,
            out_channels=desc.channels,
            kernel_size=1,
        )

        self._logit = torch.nn.Conv1d(
            in_channels=desc.channels,
            out_channels=desc.mixture_size,
            kernel_size=1,
        )
        self._mean = torch.nn.Conv1d(
            in_channels=desc.channels,
            out_channels=desc.mixture_size,
            kernel_size=1,
        )
        self._std = torch.nn.Conv1d(
            in_channels=desc.channels,
            out_channels=desc.mixture_size,
            kernel_size=1,
        )
        self._output_soft_plus_s = torch.nn.Softplus()

    def forward(self, in_tensor: torch.Tensor) -> MixtureSameFamily:
        """Возвращает смесь логнормальных распределений."""
        end = torch.relu(self._end(in_tensor))

        try:
            weights_dist = Categorical(
                logits=self._logit(end).permute(0, 2, 1),
            )  # type: ignore[no-untyped-call]
        except ValueError as err:
            raise exceptions.ModelError("error in categorical distribution") from err

        std = self._output_soft_plus_s(self._std(end)) + _EPS
        comp_dist = torch.distributions.LogNormal(
            loc=self._mean(end).permute((0, 2, 1)),
            scale=std.permute((0, 2, 1)),
        )  # type: ignore[no-untyped-call]

        return torch.distributions.MixtureSameFamily(
            mixture_distribution=weights_dist,
            component_distribution=comp_dist,
        )  # type: ignore[no-untyped-call]
