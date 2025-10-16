import matplotlib.pyplot as plt
import pandas as pd

from poptimizer.adapters import mongo
from poptimizer.domain.evolve import evolve


async def plot(repo: mongo.Repo) -> None:
    dots = [
        (model.alfa_mean, model.llh_mean, model.ver * 10) async for model in repo.get_all(evolve.Model) if model.ver
    ]

    df = pd.DataFrame(dots, columns=["alfa", "llh", "size"])

    min_llh = df["llh"].argmin()
    max_llh = df["llh"].argmax()
    min_alfa = df["alfa"].argmin()
    max_alfa = df["alfa"].argmax()

    df["color"] = [
        "red" if i in (min_alfa, min_llh) else "green" if i in (max_alfa, max_llh) else "lightgreen"
        for i in range(len(df))
    ]

    plt.figure(figsize=(10, 6))  # type: ignore[reportUnknownMemberType]
    plt.scatter(df["llh"], df["alfa"], c=df["color"], s=df["size"], alpha=0.6)  # type: ignore[reportUnknownMemberType]

    plt.xlabel("llh")  # type: ignore[reportUnknownMemberType]
    plt.ylabel("alfa")  # type: ignore[reportUnknownMemberType]
    plt.grid(visible=True, linestyle="--", alpha=0.5)  # type: ignore[reportUnknownMemberType]

    plt.show()  # type: ignore[reportUnknownMemberType]
