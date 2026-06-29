from infrastructure.rate_limit import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_allows_up_to_max_then_blocks():
    rl = SlidingWindowRateLimiter(max_requests=2, window_seconds=10, clock=FakeClock())
    assert rl.allow("ip") is True
    assert rl.allow("ip") is True
    assert rl.allow("ip") is False


def test_window_slides_so_old_hits_expire():
    clock = FakeClock()
    rl = SlidingWindowRateLimiter(max_requests=2, window_seconds=10, clock=clock)
    rl.allow("ip")
    rl.allow("ip")
    assert rl.allow("ip") is False
    clock.t = 11  # both prior hits are now outside the window
    assert rl.allow("ip") is True


def test_keys_are_independent():
    rl = SlidingWindowRateLimiter(max_requests=1, window_seconds=10, clock=FakeClock())
    assert rl.allow("a") is True
    assert rl.allow("b") is True
    assert rl.allow("a") is False
