import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RateLimiter:
    """Simple rate limiter enforcing a minimum interval between calls."""

    rate: float  # allowed calls per second
    _last_call: Optional[float] = field(default=None, init=False)

    def wait(self) -> None:
        interval = 1.0 / self.rate
        now = time.time()
        if self._last_call is not None:
            elapsed = now - self._last_call
            if elapsed < interval:
                time.sleep(interval - elapsed)
        self._last_call = time.time()
