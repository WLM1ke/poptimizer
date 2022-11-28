"""Часть сети, отвечающая за предобработку входных данных."""
import torch
from dl import data_loader, exceptions
from pydantic import BaseModel


class Desc(BaseModel):
    """Описание параметров входных данных.

    :param history_days:
        Количество дней в истории.
    :param use_bn:
        Нужно ли производить BN для входящих численных значений.
    :param num_feat_count:
        Количество количественных признаков.
    :param out_channels:
        Количество каналов на входе основной части сети.
    """

    history_days: int
    use_bn: bool
    num_feat_count: int
    out_channels: int


class Net(torch.nn.Module):
    """Часть сети, отвечающая за предобработку входных данных.

    Объединяет входные данные в единый тензор и нормализует его.
    """

    def __init__(self, desc: Desc) -> None:
        super().__init__()

        if desc.num_feat_count == 0:
            raise exceptions.ModelError("no features")

        if desc.use_bn:
            self._bn: torch.nn.BatchNorm1d | torch.nn.Identity = torch.nn.BatchNorm1d(desc.num_feat_count)
        else:
            self._bn = torch.nn.Identity()

        self._output = torch.nn.Conv1d(
            in_channels=desc.num_feat_count,
            out_channels=desc.out_channels,
            kernel_size=1,
        )

    def forward(self, batch: data_loader.Case) -> torch.Tensor:
        """Возвращает входные данные в виде одного тензора."""
        normalized = self._bn(batch[data_loader.FeatTypes.NUMERICAL])

        return self._output(normalized)  # type: ignore[no-any-return]
