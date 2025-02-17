import numpy as np
import torch
from numpy.typing import NDArray
from torch.distributions import MixtureSameFamily

from poptimizer import errors
from poptimizer.domain.dl.wave_net import backbone, head, inputs


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
        super().__init__()  # type: ignore[reportUnknownMemberType]

        self._input = inputs.Net(
            num_feat_count=num_feat_count,
            emb_size=emb_size,
            emb_seq_size=emb_seq_size,
            use_bn=cfg.use_bn,
            residual_channels=cfg.residual_channels,
        )
        self._backbone = backbone.Net(
            blocks=int(np.log2(history_days - 1)) + 1,
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
        norm_input = self._input(num_feat, emb_feat, emb_seq_feat)
        end = self._backbone(norm_input)

        return self._head(end)  # type: ignore[no-any-return]

    def llh(
        self,
        num_feat: torch.Tensor,
        emb_feat: torch.Tensor,
        emb_seq_feat: torch.Tensor,
        labels: torch.Tensor,
    ) -> torch.Tensor:
        dist = self(num_feat, emb_feat, emb_seq_feat)

        try:
            return dist.log_prob(labels).mean()
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
        dist = self(num_feat, emb_feat, emb_seq_feat)

        try:
            llh = dist.log_prob(labels).mean()
        except ValueError as err:
            raise errors.DomainError("error in categorical distribution") from err

        return llh.item(), dist.mean.cpu().numpy() - 1, dist.variance.cpu().numpy() ** 0.5

    def forecast_mean_and_std(
        self,
        num_feat: torch.Tensor,
        emb_feat: torch.Tensor,
        emb_seq_feat: torch.Tensor,
    ) -> tuple[NDArray[np.double], NDArray[np.double]]:
        dist = self(num_feat, emb_feat, emb_seq_feat)

        return dist.mean.cpu().numpy() - 1, dist.variance.cpu().numpy() ** 0.5
