import numpy as np
import torch


class _GatedBlock(torch.nn.Module):
    def __init__(self, in_channels: int, hidden_channels: int, kernels: int) -> None:
        super().__init__()  # type: ignore[reportUnknownMemberType]
        self._pad = torch.nn.ConstantPad1d(
            padding=(kernels - 1, 0),
            value=0,
        )
        self._signal = torch.nn.Conv1d(
            in_channels=in_channels,
            out_channels=hidden_channels,
            kernel_size=kernels,
            stride=1,
        )
        self._gate = torch.nn.Conv1d(
            in_channels=in_channels,
            out_channels=hidden_channels,
            kernel_size=kernels,
            stride=1,
        )
        self._output = torch.nn.Conv1d(
            in_channels=hidden_channels,
            out_channels=in_channels,
            kernel_size=1,
        )

    def forward(self, in_tensor: torch.Tensor) -> torch.Tensor:
        padded_input: torch.Tensor = self._pad(in_tensor)

        signal = torch.relu(self._signal(padded_input))
        gate = torch.sigmoid(self._gate(padded_input))
        gated_signal: torch.Tensor = self._output(signal * gate)

        return in_tensor + gated_signal


class _Blocks(torch.nn.Module):
    def __init__(
        self,
        in_channels: int,
        blocks: int,
        kernels: int,
        hidden_channels: int,
        out_channels: int,
    ) -> None:
        super().__init__()  # type: ignore[reportUnknownMemberType]

        self._blocks = torch.nn.Sequential()
        for _ in range(blocks):
            self._blocks.append(
                _GatedBlock(
                    in_channels=in_channels,
                    hidden_channels=hidden_channels,
                    kernels=kernels,
                ),
            )

        self._skip = torch.nn.Conv1d(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=1,
        )
        self._dilated_pad = torch.nn.ConstantPad1d(
            padding=(1, 0),
            value=0,
        )
        self._dilated = torch.nn.Conv1d(
            in_channels=in_channels,
            out_channels=in_channels,
            kernel_size=2,
            stride=2,
        )

    def forward(self, in_tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        gated: torch.Tensor = self._blocks(in_tensor)

        dilated: torch.Tensor = self._dilated(self._dilated_pad(gated))
        skip: torch.Tensor = self._skip(gated[:, :, -1:])

        return dilated, skip


class Net(torch.nn.Module):
    def __init__(
        self,
        history_days: int,
        in_channels: int,
        blocks: int,
        kernels: int,
        hidden_channels: int,
        out_channels: int,
    ) -> None:
        super().__init__()  # type: ignore[reportUnknownMemberType]

        self._blocks = torch.nn.ModuleList()
        blocks = int(np.log2(history_days - 1)) + 1

        for _ in range(blocks):
            self._blocks.append(
                _Blocks(
                    in_channels=in_channels,
                    blocks=blocks,
                    kernels=kernels,
                    hidden_channels=hidden_channels,
                    out_channels=out_channels,
                )
            )

        self._final_skip_conv = torch.nn.Conv1d(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=1,
        )

    def forward(self, in_tensor: torch.Tensor) -> torch.Tensor:
        blocks_iter = iter(self._blocks)

        in_tensor, skips = next(blocks_iter)(in_tensor)

        for block in blocks_iter:
            in_tensor, skip = block(in_tensor)
            skips = skips + skip

        skips = skips + self._final_skip_conv(in_tensor)

        return torch.relu(skips)
