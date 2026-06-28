import logging
from infrastructure.observability.latency import timed


def test_timed_logs_label_and_elapsed_ms(caplog):
    clock = iter([1.0, 1.5]).__next__  # start=1.0s, end=1.5s -> 500.0 ms
    with caplog.at_level(logging.INFO, logger="atom.latency"):
        with timed("StreamChat.total", clock=clock):
            pass
    msgs = [r.getMessage() for r in caplog.records if r.name == "atom.latency"]
    assert any("label=StreamChat.total" in m and "ms=500.0" in m for m in msgs)


def test_timed_logs_even_on_exception(caplog):
    clock = iter([0.0, 0.2]).__next__  # 200.0 ms
    with caplog.at_level(logging.INFO, logger="atom.latency"):
        try:
            with timed("X", clock=clock):
                raise ValueError("boom")
        except ValueError:
            pass
    assert any("label=X" in r.getMessage() and "ms=200.0" in r.getMessage()
               for r in caplog.records if r.name == "atom.latency")
