import torch
from pydantic import BaseModel
from torch import nn

from poptimizer import errors


class Cfg(BaseModel):
    use_bn: bool
    out_channels: int


class Net(torch.nn.Module):
    def __init__(
        self,
        *,
        num_feat_count: int,
        emb_size: list[int],
        use_bn: bool,
        residual_channels: int,
    ) -> None:
        super().__init__()  # type: ignore[reportUnknownMemberType]

        if num_feat_count == 0:
            raise errors.DomainError("no features")

        if use_bn:
            self._bn: nn.BatchNorm1d | nn.Identity = nn.BatchNorm1d(num_feat_count)
        else:
            self._bn = nn.Identity()

        self._output = nn.Conv1d(
            in_channels=num_feat_count,
            out_channels=residual_channels,
            kernel_size=1,
        )

        self._emb_list = nn.ModuleList()
        for size in emb_size:
            self._emb_list.append(nn.Embedding(num_embeddings=size, embedding_dim=residual_channels))

    def forward(self, num_feat: torch.Tensor, emb_feat: torch.Tensor) -> torch.Tensor:
        output = self._output(self._bn(num_feat))

        for n, layer in enumerate(self._emb_list):
            output = output + layer(emb_feat[:, n]).unsqueeze(2)

        return output
