import matplotlib.pyplot as plt
import pandas as pd

from poptimizer.evolve.evolution import evolve
from poptimizer.fsm import uow


async def plot(repo: uow.UOW) -> None:
    dots = [(model.alfa, model.llh, model.duration) async for model in repo.get_all(evolve.Model) if model.duration]
    df = pd.DataFrame(dots, columns=["alfa", "llh", "duration"])

    plt.figure(figsize=(10, 6))  # type: ignore[reportUnknownMemberType]

    scatter = plt.scatter(  # type: ignore[reportUnknownMemberType]
        df["llh"],
        df["alfa"],
        c=df["duration"],
        s=df["duration"],
        cmap="RdYlGn_r",
        alpha=0.6,
    )

    plt.colorbar(scatter, label="Seconds")  # type: ignore[reportUnknownMemberType]

    plt.xlabel("llh")  # type: ignore[reportUnknownMemberType]
    plt.ylabel("alfa")  # type: ignore[reportUnknownMemberType]
    plt.grid(visible=True, linestyle="--", alpha=0.5)  # type: ignore[reportUnknownMemberType]

    plt.show()  # type: ignore[reportUnknownMemberType]
