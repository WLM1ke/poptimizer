import torch
from pydantic import BaseModel

from poptimizer.dl import datasets, dl


class Cfg(BaseModel):
    use_bn: bool
    out_channels: int


class Net(torch.nn.Module):
    def __init__(self, num_feat_count: int, cfg: Cfg) -> None:
        super().__init__()

        if num_feat_count == 0:
            raise dl.DLError("no features")

        if cfg.use_bn:
            self._bn: torch.nn.BatchNorm1d | torch.nn.Identity = torch.nn.BatchNorm1d(num_feat_count)
        else:
            self._bn = torch.nn.Identity()

        self._output = torch.nn.Conv1d(
            in_channels=num_feat_count,
            out_channels=cfg.out_channels,
            kernel_size=1,
        )

    def forward(self, batch: datasets.Batch) -> torch.Tensor:
        normalized = self._bn(batch[datasets.FeatTypes.NUMERICAL])

        return self._output(normalized)  # type: ignore[no-any-return]
