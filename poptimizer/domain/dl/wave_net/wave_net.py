import numpy as np
import torch
from numpy.typing import NDArray
from torch.distributions import MixtureSameFamily

from poptimizer import errors
from poptimizer.domain.dl import features
from poptimizer.domain.dl.wave_net import backbone, head, inputs


class Net(torch.nn.Module):
    """WaveNet-like сеть с возможностью параметризации параметров.

    https://arxiv.org/abs/1609.03499
    """

    def __init__(
        self,
        cfg: backbone.Cfg,
        num_feat_count: int,
        history_days: int,
    ) -> None:
        super().__init__()  # type: ignore[reportUnknownMemberType]

        self._input = inputs.Net(
            num_feat_count=num_feat_count,
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

    def forward(self, batch: features.Batch) -> MixtureSameFamily:
        norm_input = self._input(batch)
        end = self._backbone(norm_input)

        return self._head(end)  # type: ignore[no-any-return]

    def llh(self, batch: features.Batch) -> torch.Tensor:
        dist = self(batch)

        labels = batch[features.FeatTypes.LABEL]

        try:
            return dist.log_prob(labels).mean()
        except ValueError as err:
            raise errors.DomainError("error in categorical distribution") from err

    def loss_and_forecast_mean_and_std(
        self,
        batch: features.Batch,
    ) -> tuple[float, NDArray[np.double], NDArray[np.double]]:
        """Minus Normal Log Likelihood and forecast means and vars."""
        dist = self(batch)

        labels = batch[features.FeatTypes.LABEL]

        try:
            llh = dist.log_prob(labels).mean()
        except ValueError as err:
            raise errors.DomainError("error in categorical distribution") from err

        return llh.item(), dist.mean.cpu().numpy() - 1, dist.variance.cpu().numpy() ** 0.5

    def forecast_mean_and_std(
        self,
        batch: features.Batch,
    ) -> tuple[NDArray[np.double], NDArray[np.double]]:
        dist = self(batch)

        return dist.mean.cpu().numpy() - 1, dist.variance.cpu().numpy() ** 0.5
