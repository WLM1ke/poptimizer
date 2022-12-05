"""Часть сети, отвечающая за предобработку входных данных."""
import torch
from pydantic import BaseModel

from poptimizer.dl import datasets, exceptions


class Desc(BaseModel):
    """Описание параметров входных данных.

    :param use_bn:
        Нужно ли производить BN для входящих численных значений.
    :param out_channels:
        Количество каналов на входе основной части сети.
    """

    use_bn: bool
    out_channels: int


class Net(torch.nn.Module):
    """Часть сети, отвечающая за предобработку входных данных.

    Объединяет входные данные в единый тензор и нормализует его.
    """

    def __init__(self, num_feat_count: int, desc: Desc) -> None:
        super().__init__()

        if num_feat_count == 0:
            raise exceptions.ModelError("no features")

        if desc.use_bn:
            self._bn: torch.nn.BatchNorm1d | torch.nn.Identity = torch.nn.BatchNorm1d(num_feat_count)
        else:
            self._bn = torch.nn.Identity()

        self._output = torch.nn.Conv1d(
            in_channels=num_feat_count,
            out_channels=desc.out_channels,
            kernel_size=1,
        )

    def forward(self, batch: datasets.Batch) -> torch.Tensor:
        """Возвращает входные данные в виде одного тензора."""
        normalized = self._bn(batch[datasets.FeatTypes.NUMERICAL])

        return self._output(normalized)  # type: ignore[no-any-return]
