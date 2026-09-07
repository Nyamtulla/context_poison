"""Shared HTTP plumbing: per-client rate limiting + exponential backoff on
429/5xx (SRS NFR-1). Every API client wraps requests through `ThrottledClient`
so backoff behavior is consistent and doesn't get reimplemented per-source.
"""
from __future__ import annotations

import threading
import time

import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


class RateLimiter:
    """Simple min-interval throttle, thread-safe (clients may be used from
    a BFS snowball loop that could parallelize later)."""

    def __init__(self, rps: float):
        self.min_interval = (1.0 / rps) if rps > 0 else 0.0
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_call = time.monotonic()


class RetryableStatusError(Exception):
    def __init__(self, response: requests.Response):
        self.response = response
        super().__init__(f"HTTP {response.status_code} for {response.url}")


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(
        exc,
        (requests.exceptions.ConnectionError, requests.exceptions.Timeout, RetryableStatusError),
    )


class ThrottledClient:
    """requests.Session wrapper: rate-limited + retries 429/5xx with
    exponential backoff, honoring Retry-After when the server sends one."""

    def __init__(
        self,
        rps: float,
        max_retries: int = 5,
        timeout: float = 30.0,
        headers: dict | None = None,
    ):
        self.session = requests.Session()
        if headers:
            self.session.headers.update({k: v for k, v in headers.items() if v})
        self.limiter = RateLimiter(rps)
        self.timeout = timeout
        self._retrying_get = retry(
            reraise=True,
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=60),
            retry=retry_if_exception(_is_retryable),
        )(self._get_once)

    def _get_once(self, url: str, **kwargs) -> requests.Response:
        self.limiter.wait()
        resp = self.session.get(url, timeout=self.timeout, **kwargs)
        if resp.status_code == 429 or resp.status_code >= 500:
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    time.sleep(float(retry_after))
                except ValueError:
                    pass
            raise RetryableStatusError(resp)
        return resp

    def get(self, url: str, **kwargs) -> requests.Response:
        return self._retrying_get(url, **kwargs)
