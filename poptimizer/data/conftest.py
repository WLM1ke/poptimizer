import asyncio
from typing import Iterator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()
