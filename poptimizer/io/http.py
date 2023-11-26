import asyncio
import ssl
from collections.abc import Awaitable, Callable, Iterable, Mapping
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, Final, Literal, override

import aiohttp
from aiohttp import client_reqrep, helpers, typedefs, web_exceptions

from poptimizer.core import errors

_HEADERS: Final = {
    "User-Agent": "POptimizer",
    "Connection": "keep-alive",
}


class HTTPClient(aiohttp.ClientSession):
    def __init__(
        self,
        con_per_host: int,
        retries: int,
        first_retry: timedelta,
        backoff_factor: float,
    ) -> None:
        super().__init__(
            connector=aiohttp.TCPConnector(limit_per_host=con_per_host),
            headers=_HEADERS,
        )
        self._retries = max(0, retries)
        self._first_retry = first_retry.total_seconds()
        self._backoff_factor = backoff_factor

    @override
    async def _request(  # noqa: PLR0913
        self,
        method: str,
        str_or_url: typedefs.StrOrURL,
        *,
        params: Mapping[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        cookies: typedefs.LooseCookies | None = None,
        headers: typedefs.LooseHeaders | None = None,
        skip_auto_headers: Iterable[str] | None = None,
        auth: helpers.BasicAuth | None = None,
        allow_redirects: bool = True,
        max_redirects: int = 10,
        compress: str | None = None,
        chunked: bool | None = None,
        expect100: bool = False,
        raise_for_status: bool | Callable[[client_reqrep.ClientResponse], Awaitable[None]] | None = None,
        read_until_eof: bool = True,
        proxy: typedefs.StrOrURL | None = None,
        proxy_auth: helpers.BasicAuth | None = None,
        timeout: aiohttp.ClientTimeout | helpers._SENTINEL = helpers.sentinel,  # type: ignore[reportPrivateUsage]  # noqa: SLF001
        verify_ssl: bool | None = None,
        fingerprint: bytes | None = None,
        ssl_context: ssl.SSLContext | None = None,
        ssl: ssl.SSLContext | Literal[False] | client_reqrep.Fingerprint | None = None,
        server_hostname: str | None = None,
        proxy_headers: typedefs.LooseHeaders | None = None,
        trace_request_ctx: SimpleNamespace | None = None,
        read_bufsize: int | None = None,
        auto_decompress: bool | None = None,
        max_line_size: int | None = None,
        max_field_size: int | None = None,
    ) -> aiohttp.ClientResponse:
        for attempt in range(self._retries + 1):
            await asyncio.sleep(self._delay(attempt))

            try:
                resp = await super()._request(
                    method=method,
                    str_or_url=str_or_url,
                    params=params,
                    data=data,
                    json=json,
                    cookies=cookies,
                    headers=headers,
                    skip_auto_headers=skip_auto_headers,
                    auth=auth,
                    allow_redirects=allow_redirects,
                    max_redirects=max_redirects,
                    compress=compress,
                    chunked=chunked,
                    expect100=expect100,
                    raise_for_status=raise_for_status,
                    read_until_eof=read_until_eof,
                    proxy=proxy,
                    proxy_auth=proxy_auth,
                    timeout=timeout,
                    verify_ssl=verify_ssl,
                    fingerprint=fingerprint,
                    ssl_context=ssl_context,
                    ssl=ssl,
                    server_hostname=server_hostname,
                    proxy_headers=proxy_headers,
                    trace_request_ctx=trace_request_ctx,
                    read_bufsize=read_bufsize,
                    auto_decompress=auto_decompress,
                    max_line_size=max_line_size,
                    max_field_size=max_field_size,
                )
            except (aiohttp.ClientError, asyncio.TimeoutError):
                continue

            if resp.status >= web_exceptions.HTTPInternalServerError.status_code:
                continue

            return resp

        raise errors.AdaptersError(f"http request failed after {self._retries} retries")

    def _delay(self, attempt: int) -> float:
        if attempt == 0:
            return 0

        return self._first_retry * self._backoff_factor ** (attempt - 1)
