import math
from typing import TYPE_CHECKING, cast

import numpy as np
import torch

from poptimizer.core import errors
from poptimizer.evolve.dl.wave_net import backbone, head, inputs

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from torch.distributions import MixtureSameFamily


class Net(torch.nn.Module):
    """WaveNet-like сеть с возможностью параметризации параметров.

    https://arxiv.org/abs/1609.03499
    """

    def __init__(
        self,
        cfg: backbone.Cfg,
        history_days: int,
        num_feat_count: int,
        emb_size: list[int],
        emb_seq_size: list[int],
    ) -> None:
        super().__init__()

        self._input = inputs.Net(
            num_feat_count=num_feat_count,
            emb_size=emb_size,
            emb_seq_size=emb_seq_size,
            use_bn=cfg.use_bn,
            residual_channels=cfg.residual_channels,
        )
        self._backbone = backbone.Net(
            blocks=int(math.log2(history_days - 1)) + 1,
            cfg=cfg,
        )
        self._head = head.Net(
            skip_channels=cfg.skip_channels,
            head_channels=cfg.head_channels,
            mixture_size=cfg.mixture_size,
        )

    def forward(
        self,
        num_feat: torch.Tensor,
        emb_feat: torch.Tensor,
        emb_seq_feat: torch.Tensor,
    ) -> MixtureSameFamily:
        norm_input = cast("torch.Tensor", self._input(num_feat, emb_feat, emb_seq_feat))
        end = cast("torch.Tensor", self._backbone(norm_input))

        return cast("MixtureSameFamily", self._head(end))

    def llh(
        self,
        num_feat: torch.Tensor,
        emb_feat: torch.Tensor,
        emb_seq_feat: torch.Tensor,
        labels: torch.Tensor,
    ) -> torch.Tensor:
        dist = cast("MixtureSameFamily", self(num_feat, emb_feat, emb_seq_feat))

        try:
            return dist.log_prob(labels).mean()  # pyright: ignore[reportUnknownMemberType]
        except ValueError as err:
            raise errors.DomainError("error in categorical distribution") from err

    def loss_and_forecast_mean_and_std(
        self,
        num_feat: torch.Tensor,
        emb_feat: torch.Tensor,
        emb_seq_feat: torch.Tensor,
        labels: torch.Tensor,
    ) -> tuple[float, NDArray[np.double], NDArray[np.double]]:
        """Minus Normal Log Likelihood and forecast means and vars."""
        dist = cast("MixtureSameFamily", self(num_feat, emb_feat, emb_seq_feat))

        try:
            llh = dist.log_prob(labels).mean()  # pyright: ignore[reportUnknownMemberType]
        except ValueError as err:
            raise errors.DomainError("error in categorical distribution") from err

        return llh.item(), dist.mean.cpu().numpy() - 1, np.sqrt(dist.variance.cpu().numpy())

    def forecast_mean_and_std(
        self,
        num_feat: torch.Tensor,
        emb_feat: torch.Tensor,
        emb_seq_feat: torch.Tensor,
    ) -> tuple[NDArray[np.double], NDArray[np.double]]:
        dist = cast("MixtureSameFamily", self(num_feat, emb_feat, emb_seq_feat))

        return dist.mean.cpu().numpy() - 1, np.sqrt(dist.variance.cpu().numpy())
