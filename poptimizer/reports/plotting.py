# Typed seam over matplotlib's pyplot.
from collections.abc import Sequence
from io import BytesIO
from typing import TYPE_CHECKING, Literal, cast

import matplotlib.pyplot as plt

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd
    from matplotlib.axes import Axes
    from matplotlib.collections import PathCollection
    from matplotlib.figure import Figure
    from matplotlib.text import Text
    from numpy.typing import NDArray


def figure(figsize: tuple[float, float]) -> None:
    plt.figure(figsize=figsize)  # pyright: ignore[reportUnknownMemberType]


def subplots(nrows: int, ncols: int, *, figsize: tuple[float, float]) -> tuple[Figure, Axes]:
    fig, ax = cast("tuple[Figure, Axes]", plt.subplots(nrows, ncols, figsize=figsize))

    return fig, ax


def scatter(  # noqa: PLR0913
    x: pd.Series[float],
    y: pd.Series[float],
    *,
    c: pd.Series[float],
    s: pd.Series[float],
    cmap: str,
    alpha: float,
) -> PathCollection:
    return plt.scatter(x, y, c=c, s=s, cmap=cmap, alpha=alpha)  # pyright: ignore[reportUnknownMemberType]


def colorbar(mappable: PathCollection, *, label: str) -> None:
    plt.colorbar(mappable, label=label)  # pyright: ignore[reportUnknownMemberType]


def xlabel(label: str) -> None:
    plt.xlabel(label)  # pyright: ignore[reportUnknownMemberType]


def ylabel(label: str) -> None:
    plt.ylabel(label)  # pyright: ignore[reportUnknownMemberType]


def grid(  # noqa: PLR0913
    *,
    visible: bool = True,
    which: Literal["major", "minor", "both"] = "major",
    lw: float = 0.5,
    c: str = "black",
    alpha: float = 0.3,
    linestyle: str = "-",
) -> None:
    plt.grid(visible=visible, which=which, lw=lw, c=c, alpha=alpha, linestyle=linestyle)  # pyright: ignore[reportUnknownMemberType]


def show() -> None:
    plt.show()  # pyright: ignore[reportUnknownMemberType]


def tick_params(*, bottom: bool, top: bool, left: bool, right: bool) -> None:
    plt.tick_params(bottom=bottom, top=top, left=left, right=right)  # pyright: ignore[reportUnknownMemberType]


def plot(values: NDArray[np.float64]) -> None:
    plt.plot(values)  # pyright: ignore[reportUnknownMemberType]


def yticks(*, fontsize: int) -> None:
    plt.yticks(fontsize=fontsize)  # pyright: ignore[reportUnknownMemberType]


def xticks(locations: Sequence[int], labels: Sequence[str], *, fontsize: int) -> None:
    plt.xticks(locations, labels, fontsize=fontsize)  # pyright: ignore[reportUnknownMemberType]


def legend(labels: Sequence[str], *, fontsize: int, frameon: bool) -> None:
    plt.legend(labels, fontsize=fontsize, frameon=frameon)  # pyright: ignore[reportUnknownMemberType]


def savefig(file: BytesIO, *, dpi: int, file_format: str = "png", transparent: bool = True) -> None:
    plt.savefig(file, dpi=dpi, format=file_format, transparent=transparent)  # pyright: ignore[reportUnknownMemberType]


def pie(  # noqa: PLR0913
    ax: Axes,
    values: Sequence[float],
    labels: Sequence[str],
    *,
    startangle: int,
    counterclock: bool,
    labeldistance: float,
) -> list[Text]:
    _, texts = ax.pie(  # pyright: ignore[reportUnknownVariableType]
        values,
        labels=labels,
        startangle=startangle,
        counterclock=counterclock,
        labeldistance=labeldistance,
    )

    return cast("list[Text]", texts)


def setp(texts: Sequence[Text], *, size: int) -> None:
    plt.setp(texts, size=size)  # pyright: ignore[reportUnknownMemberType]
