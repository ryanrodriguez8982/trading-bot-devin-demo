import logging
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, TypeVar

import ccxt

from trading_bot.notify import send as notify_send


logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryPolicy:
    """Retry helper with exponential backoff, jitter and circuit breaker."""

    retries: int = 3
    backoff: float = 0.5
    jitter: float = 0.1
    failure_threshold: int = 5
    recovery_time: float = 30.0
    _failures: int = field(default=0, init=False)
    _opened_at: Optional[float] = field(default=None, init=False)

    def _circuit_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.time() - self._opened_at >= self.recovery_time:
            self._failures = 0
            self._opened_at = None
            return False
        return True

    def _record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold and self._opened_at is None:
            self._opened_at = time.time()

    def _record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        attempt = 0
        while True:
            if self._circuit_open():
                logger.error(f"Circuit breaker open for {func.__name__}")
                notify_send(f"Circuit breaker open for {func.__name__}")
                raise RuntimeError("circuit breaker open")
            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            except Exception as e:  # pragma: no cover - generic catch
                attempt += 1
                self._record_failure()
                if isinstance(e, ccxt.NetworkError):
                    logger.warning(
                        f"{func.__name__} network error on attempt {attempt}: {e}",
                        exc_info=True,
                    )
                    if attempt > self.retries:
                        logger.error(
                            f"{func.__name__} network error after {self.retries} retries: {e}",
                            exc_info=True,
                        )
                        raise
                    sleep = min(self.backoff * (2 ** (attempt - 1)), 1.0)
                else:
                    logger.warning(
                        f"{func.__name__} failed on attempt {attempt}: {e}",
                        exc_info=True,
                    )
                    if attempt > self.retries:
                        logger.error(
                            f"{func.__name__} failed after {self.retries} retries: {e}",
                            exc_info=True,
                        )
                        raise
                    sleep = self.backoff * (2 ** (attempt - 1))
                sleep += random.uniform(0, self.jitter)
                time.sleep(sleep)


def default_retry() -> RetryPolicy:
    """Return a default RetryPolicy instance."""
    return RetryPolicy()
