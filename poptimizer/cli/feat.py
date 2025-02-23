import asyncio
import contextlib
import statistics
from collections import Counter

import uvloop

from poptimizer import config
from poptimizer.adapters import logger, mongo
from poptimizer.domain.evolve import evolve


async def _run() -> None:
    cfg = config.Cfg()
    err: Exception | None = None

    async with contextlib.AsyncExitStack() as stack:
        lgr = await stack.enter_async_context(logger.init())

        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))
        repo = mongo.Repo(mongo_db)

        lgr.info("Starting...")

        try:
            count = 0
            history_days: list[int] = []
            features: Counter[str] = Counter()

            async for model in repo.get_all(evolve.Model):
                if not model.ver:
                    continue

                count += 1
                batch = model.phenotype["batch"]
                history_days.append(batch["history_days"])
                features.update({"use_lag_feat": batch["use_lag_feat"]})
                features.update(batch["num_feats"])
                features.update(batch["emb_feats"])
                features.update(batch["emb_seq_feats"])

            lgr.info("Count - %d", count)
            lgr.info(
                "History days - %d - %d - %d",
                min(history_days),
                statistics.median(history_days),
                max(history_days),
            )
            for feature, feat_count in features.most_common():
                lgr.info(f"Feature {feature} - {feat_count / count:.2%}")

            lgr.info("Finished")
        except asyncio.CancelledError:
            lgr.info("Shutdown finished")
        except Exception as exc:  # noqa: BLE001
            lgr.warning("Shutdown abnormally: %r", exc)
            err = exc

    if err:
        raise err


def stats() -> None:
    """Features genotype statistics."""
    uvloop.run(_run())


if __name__ == "__main__":
    stats()
