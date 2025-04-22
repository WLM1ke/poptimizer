import logging
import statistics
from collections import Counter
from typing import Any

from poptimizer.adapters import mongo
from poptimizer.domain.evolve import evolve


async def report(repo: mongo.Repo) -> None:
    lgr = logging.getLogger()

    evolution = await repo.get(evolve.Evolution)

    data: list[tuple[str, Any]] = [
        ("Tickers", len(evolution.tickers)),
        ("Forecast days", evolution.forecast_days),
        ("Test days", int(evolution.test_days)),
        ("Min return days", evolution.minimal_returns_days),
    ]

    count = 0
    risk_aversion: list[float] = []
    history_days: list[int] = []
    features: Counter[str] = Counter()

    async for model in repo.get_all(evolve.Model):
        if not model.ver:
            continue

        count += 1
        phenotype = model.phenotype
        risk_aversion.append(1 - phenotype["risk"]["risk_tolerance"])
        batch = phenotype["batch"]
        history_days.append(batch["history_days"])
        features.update({"use_lag_feat": batch["use_lag_feat"]})
        features.update(batch["num_feats"])
        features.update(batch["emb_feats"])
        features.update(batch["emb_seq_feats"])

    data.append(("Model count", count))
    data.append(
        (
            "Risk aversion",
            f"{min(risk_aversion):.2%} - {statistics.median(risk_aversion):.2%} - {max(risk_aversion):.2%}",
        )
    )
    data.append(
        (
            "History days",
            f"{min(history_days)} - {statistics.median(history_days):.0f} - {max(history_days)}",
        )
    )

    for feature, feat_count in features.most_common():
        data.append((f"Feature {feature}", f"{feat_count / count:.2%}"))

    max_name = max(len(name) for name, _ in data)

    lgr.info("Evolution statistics")
    for name, value in data:
        lgr.info(f"{name:<{max_name}} {value}")
