import torch
from pydantic import BaseModel

from poptimizer.dl import dl


class Desc(BaseModel):
    use_bn: bool
    out_channels: int


class Net(torch.nn.Module):
    def __init__(self, in_channels: int, out_channels: int, *, use_bn: bool) -> None:
        super().__init__()  # type: ignore[reportUnknownMemberType]

        if in_channels == 0:
            raise dl.DLError("no features")

        self._bn: torch.nn.BatchNorm1d | torch.nn.Identity = torch.nn.Identity()
        if use_bn:
            self._bn: torch.nn.BatchNorm1d | torch.nn.Identity = torch.nn.BatchNorm1d(in_channels)

        self._output = torch.nn.Conv1d(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=1,
        )

    def forward(self, batch: dl.Batch) -> torch.Tensor:
        normalized: torch.Tensor = self._bn(batch[dl.FeatTypes.NUMERICAL])

        return self._output(normalized)
