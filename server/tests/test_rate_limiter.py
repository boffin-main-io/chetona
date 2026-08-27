import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rate_limiter import RateLimiter


def test_burst_allowed_then_blocked():
    limiter = RateLimiter(capacity=3, refill_per_second=0.1)
    identity = "player-1"
    results = [limiter.allow(identity) for _ in range(5)]
    assert results[:3] == [True, True, True]
    assert results[3] is False


def test_different_identities_independent():
    limiter = RateLimiter(capacity=1, refill_per_second=0.1)
    assert limiter.allow("alice") is True
    assert limiter.allow("bob") is True
    assert limiter.allow("alice") is False


def test_refills_over_time():
    limiter = RateLimiter(capacity=1, refill_per_second=100.0)  # fast refill for the test
    identity = "player-2"
    assert limiter.allow(identity) is True
    assert limiter.allow(identity) is False
    time.sleep(0.05)
    assert limiter.allow(identity) is True
