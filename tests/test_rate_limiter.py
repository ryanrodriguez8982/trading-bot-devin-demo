import time

from trading_bot.utils.rate_limit import RateLimiter


def test_rate_limiter_waits():
    limiter = RateLimiter(rate=20)  # 0.05s interval
    start = time.time()
    for _ in range(5):
        limiter.wait()
    elapsed = time.time() - start
    assert elapsed >= 0.2
