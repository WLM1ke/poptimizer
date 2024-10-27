import torch
from pydantic import BaseModel

from poptimizer import errors
from poptimizer.domain.dl import datasets


class Cfg(BaseModel):
    use_bn: bool
    out_channels: int


class Net(torch.nn.Module):
    def __init__(
        self,
        *,
        num_feat_count: int,
        use_bn: bool,
        residual_channels: int,
    ) -> None:
        super().__init__()  # type: ignore[reportUnknownMemberType]

        if num_feat_count == 0:
            raise errors.DomainError("no features")

        if use_bn:
            self._bn: torch.nn.BatchNorm1d | torch.nn.Identity = torch.nn.BatchNorm1d(num_feat_count)
        else:
            self._bn = torch.nn.Identity()

        self._output = torch.nn.Conv1d(
            in_channels=num_feat_count,
            out_channels=residual_channels,
            kernel_size=1,
        )

    def forward(self, batch: datasets.Batch) -> torch.Tensor:
        normalized = self._bn(batch[datasets.FeatTypes.NUMERICAL])

        return self._output(normalized)  # type: ignore[no-any-return]
