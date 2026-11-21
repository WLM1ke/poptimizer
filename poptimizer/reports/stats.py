import logging
import statistics
from collections import Counter
from datetime import timedelta

from poptimizer.evolve.models import evolve, genetics
from poptimizer.runtime import uow


async def report(lgr: logging.Logger, repo: uow.Repo) -> None:
    evolution = await repo.get(evolve.Evolution)

    data: list[tuple[str, object]] = [
        ("Tickers", len(evolution.tickers)),
        ("Forecast days", evolution.forecast_days),
        ("Test days", int(evolution.test_days)),
        ("Min return days", evolution.minimal_returns_days),
    ]

    count = 0
    risk_aversion: list[float] = []
    history_days: list[int] = []
    duration: list[float] = []
    features: Counter[str] = Counter()

    async for model in repo.get_all(evolve.Model):
        if not model.duration:
            continue

        count += 1
        phenotype = model.phenotype
        risk = genetics.phenotype_mapping(phenotype, "risk")
        risk_aversion.append(1 - genetics.phenotype_float(risk, "risk_tolerance"))
        batch = genetics.phenotype_mapping(phenotype, "batch")
        history_days.append(genetics.phenotype_int(batch, "history_days"))
        duration.append(model.duration)
        features.update({"use_lag_feat": genetics.phenotype_bool(batch, "use_lag_feat")})
        features.update(genetics.phenotype_flags(batch, "num_feats"))
        features.update(genetics.phenotype_flags(batch, "emb_feats"))
        features.update(genetics.phenotype_flags(batch, "emb_seq_feats"))

    data.append(("Model count", count))
    data.append(
        (
            "Duration",
            (
                f"{timedelta(seconds=round(min(duration)))} - "
                f"{timedelta(seconds=round(statistics.median(duration)))} - {timedelta(seconds=round(max(duration)))}"
            ),
        )
    )
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
