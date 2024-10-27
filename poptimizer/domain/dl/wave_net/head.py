import torch
from pydantic import BaseModel
from torch.distributions import Categorical, MixtureSameFamily

from poptimizer import errors


class Cfg(BaseModel):
    channels: int
    mixture_size: int


class Net(torch.nn.Module):
    def __init__(
        self,
        *,
        skip_channels: int,
        head_channels: int,
        mixture_size: int,
    ) -> None:
        super().__init__()  # type: ignore[reportUnknownMemberType]

        self.register_buffer(
            "_eps",
            torch.tensor(torch.finfo().eps),
        )

        self._end = torch.nn.Conv1d(
            in_channels=skip_channels,
            out_channels=head_channels,
            kernel_size=1,
        )

        self._logit = torch.nn.Conv1d(
            in_channels=head_channels,
            out_channels=mixture_size,
            kernel_size=1,
        )
        self._mean = torch.nn.Conv1d(
            in_channels=head_channels,
            out_channels=mixture_size,
            kernel_size=1,
        )
        self._std = torch.nn.Conv1d(
            in_channels=head_channels,
            out_channels=mixture_size,
            kernel_size=1,
        )
        self._output_soft_plus_s = torch.nn.Softplus()

    def forward(self, in_tensor: torch.Tensor) -> MixtureSameFamily:
        end = torch.relu(self._end(in_tensor))

        try:
            weights_dist = Categorical(
                logits=self._logit(end).permute(0, 2, 1),
            )  # type: ignore[no-untyped-call]
        except ValueError as err:
            raise errors.DomainError("error in categorical distribution") from err

        std = self._output_soft_plus_s(self._std(end)) + self._eps
        comp_dist = torch.distributions.LogNormal(
            loc=self._mean(end).permute((0, 2, 1)),
            scale=std.permute((0, 2, 1)),
        )  # type: ignore[no-untyped-call]

        return torch.distributions.MixtureSameFamily(
            mixture_distribution=weights_dist,
            component_distribution=comp_dist,
        )  # type: ignore[no-untyped-call]
