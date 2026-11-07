import tqdm
import tqdm.std

from poptimizer.evolve.dl import pool, worker


def _check_lock_worker(_: int, __: int) -> bool:
    worker._set_tqdm_thread_lock()

    with tqdm.tqdm(total=1):
        pass

    return not hasattr(tqdm.std.TqdmDefaultWriteLock, "mp_lock")


async def test_worker_never_creates_tqdm_mp_lock():
    async with pool.PoolTrainingRunner(_check_lock_worker) as runner:
        assert await runner(0, 0) is True
