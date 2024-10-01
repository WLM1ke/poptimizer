import numpy as np
import torch
from numpy.typing import NDArray
from torch.distributions import MixtureSameFamily

from poptimizer.dl import dl
from poptimizer.dl.wave_net import backbone, head, inputs


class Net(torch.nn.Module):
    """WaveNet-like сеть с возможностью параметризации параметров.

    https://arxiv.org/abs/1609.03499
    """

    def __init__(
        self,
        *,
        use_bn: bool,
        history_days: int,
        forecast_days: int,
        in_channels: int,
        backbone_channels: int,
        blocks: int,
        kernels: int,
        hidden_channels: int,
        head_channels: int,
        out_channels: int,
        mixture_size: int,
    ) -> None:
        super().__init__()  # type: ignore[reportUnknownMemberType]

        self.register_buffer(
            "_llh_adj",
            torch.log(torch.tensor(forecast_days, dtype=torch.float)) / 2,
        )
        self._input = inputs.Net(
            in_channels=in_channels,
            out_channels=backbone_channels,
            use_bn=use_bn,
        )
        self._backbone = backbone.Net(
            history_days=history_days,
            in_channels=backbone_channels,
            blocks=blocks,
            kernels=kernels,
            hidden_channels=hidden_channels,
            out_channels=head_channels,
        )
        self._head = head.Net(
            in_channels=head_channels,
            out_channels=out_channels,
            mixture_size=mixture_size,
        )

    def forward(self, batch: dl.Batch) -> MixtureSameFamily:
        norm_input = self._input(batch)
        end = self._backbone(norm_input)

        return self._head(end)

    def llh(self, batch: dl.Batch) -> torch.Tensor:
        """Минус Log Likelihood с поправкой, обеспечивающей сопоставимость при разной длине прогноза."""
        dist = self(batch)

        labels = batch[dl.FeatTypes.LABEL1P]

        try:
            return self._llh_adj.add(dist.log_prob(labels).mean())
        except ValueError as err:
            raise dl.DLError("error in categorical distribution") from err

    def loss_and_forecast_mean_and_var(
        self,
        batch: dl.Batch,
    ) -> tuple[float, NDArray[np.double], NDArray[np.double]]:
        dist = self(batch)

        labels = batch[dl.FeatTypes.LABEL1P]

        try:
            llh = self._llh_adj.add(dist.log_prob(labels).mean())
        except ValueError as err:
            raise dl.DLError("error in categorical distribution") from err

        return llh.item(), dist.mean.numpy(), dist.variance.numpy()
