import numpy as np
import torch
from numpy.typing import NDArray
from pydantic import BaseModel
from torch.distributions import MixtureSameFamily

from poptimizer.dl import datasets, dl
from poptimizer.dl.wave_net import backbone, head, inputs


class Cfg(BaseModel):
    input: inputs.Cfg
    backbone: backbone.Cfg
    head: head.Cfg


class Net(torch.nn.Module):
    """WaveNet-like сеть с возможностью параметризации параметров.

    https://arxiv.org/abs/1609.03499
    """

    def __init__(
        self,
        cfg: Cfg,
        num_feat_count: int,
        history_days: int,
        forecast_days: int,
    ) -> None:
        super().__init__()

        self.register_buffer("_llh_adj", torch.log(torch.tensor(forecast_days, dtype=torch.float)) / 2)

        self._input = inputs.Net(
            num_feat_count=num_feat_count,
            cfg=cfg.input,
        )
        self._backbone = backbone.Net(
            history_days=history_days,
            in_channels=cfg.input.out_channels,
            desc=cfg.backbone,
        )
        self._head = head.Net(
            in_channels=cfg.backbone.out_channels,
            cfg=cfg.head,
        )

    def forward(self, batch: datasets.Batch) -> MixtureSameFamily:
        norm_input = self._input(batch)
        end = self._backbone(norm_input)

        return self._head(end)  # type: ignore[no-any-return]

    def llh(self, batch: datasets.Batch) -> torch.Tensor:
        dist = self(batch)

        labels = batch[datasets.FeatTypes.LABEL1P]

        try:
            return self._llh_adj.add(dist.log_prob(labels).mean())
        except ValueError as err:
            raise dl.DLError("error in categorical distribution") from err

    def loss_and_forecast_mean_and_var(
        self,
        batch: datasets.Batch,
    ) -> tuple[float, NDArray[np.double], NDArray[np.double]]:
        """Minus Normal Log Likelihood and forecast means and vars."""
        dist = self(batch)

        labels = batch[datasets.FeatTypes.LABEL1P]

        try:
            llh = self._llh_adj.add(dist.log_prob(labels).mean())
        except ValueError as err:
            raise dl.DLError("error in categorical distribution") from err

        return llh.item(), dist.mean.cpu().numpy(), dist.variance.cpu().numpy()
