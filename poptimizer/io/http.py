import asyncio
import ssl
from collections.abc import Iterable, Mapping
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, Final

import aiohttp
from aiohttp import helpers, typedefs, web_exceptions

from poptimizer.core import errors

_CONNECTIONS_PER_HOST: Final = 10

_RETRIES: Final = 3
_FIRST_RETRY: Final = timedelta(seconds=600)
_BACKOFF_FACTOR: Final = 2

_APP_NAME: Final = "POptimizer"
_HEADERS: Final = {
    "User-Agent": _APP_NAME,
    "Connection": "keep-alive",
}


class HTTPClient(aiohttp.ClientSession):
    def __init__(
        self,
        con_per_host: int = _CONNECTIONS_PER_HOST,
        retries: int = _RETRIES,
        first_retry: timedelta = _FIRST_RETRY,
        backoff_factor: float = _BACKOFF_FACTOR,
    ) -> None:
        super().__init__(
            connector=aiohttp.TCPConnector(limit_per_host=con_per_host),
            headers=_HEADERS,
        )
        self._retries = retries
        self._first_retry = first_retry.total_seconds()
        self._backoff_factor = backoff_factor

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
        auth: aiohttp.BasicAuth | None = None,
        allow_redirects: bool = True,
        max_redirects: int = 10,
        compress: str | None = None,
        chunked: bool | None = None,
        expect100: bool = False,
        raise_for_status: bool | None = None,
        read_until_eof: bool = True,
        proxy: typedefs.StrOrURL | None = None,
        proxy_auth: aiohttp.BasicAuth | None = None,
        timeout: aiohttp.ClientTimeout | object = helpers.sentinel,
        verify_ssl: bool | None = None,
        fingerprint: bytes | None = None,
        ssl_context: ssl.SSLContext | None = None,
        ssl: ssl.SSLContext | bool | aiohttp.Fingerprint | None = None,
        proxy_headers: typedefs.LooseHeaders | None = None,
        trace_request_ctx: SimpleNamespace | None = None,
        read_bufsize: int | None = None,
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
                    proxy_headers=proxy_headers,
                    trace_request_ctx=trace_request_ctx,
                    read_bufsize=read_bufsize,
                )
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                if attempt < self._retries:
                    continue

                raise errors.AdaptersError(f"http request failed after {attempt} retries") from err

            if attempt < self._retries and resp.status >= web_exceptions.HTTPInternalServerError.status_code:
                continue

        return resp

    def _delay(self, attempt: int) -> float:
        if attempt == 0:
            return 0

        return self._first_retry * self._backoff_factor ** (attempt - 1)
