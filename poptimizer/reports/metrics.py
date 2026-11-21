import pandas as pd

from poptimizer.evolve.models import evolve
from poptimizer.reports import plotting
from poptimizer.runtime import uow


async def plot(repo: uow.Repo) -> None:
    dots = [(model.alfa, model.llh, model.duration) async for model in repo.get_all(evolve.Model) if model.duration]
    df = pd.DataFrame(dots, columns=["alfa", "llh", "duration"])

    plotting.figure(figsize=(10, 6))

    scatter = plotting.scatter(
        df["llh"],
        df["alfa"],
        c=df["duration"],
        s=df["duration"],
        cmap="RdYlGn_r",
        alpha=0.6,
    )

    plotting.colorbar(scatter, label="Seconds")

    plotting.xlabel("llh")
    plotting.ylabel("alfa")
    plotting.grid(visible=True, linestyle="--", alpha=0.5)

    plotting.show()
