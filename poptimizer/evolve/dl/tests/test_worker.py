import tqdm
import tqdm.std

from poptimizer.evolve.dl import pool, worker


def _check_lock_worker(_: int, _second: int) -> bool:
    worker._set_tqdm_thread_lock()  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    with tqdm.tqdm(total=1):
        pass

    return not hasattr(tqdm.std.TqdmDefaultWriteLock, "mp_lock")  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownArgumentType]


async def test_worker_never_creates_tqdm_mp_lock() -> None:
    async with pool.PoolTrainingRunner(_check_lock_worker) as runner:
        assert await runner(0, 0) is True
