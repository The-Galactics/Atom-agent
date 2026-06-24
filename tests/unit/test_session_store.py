from application.agents.session_store import SessionStore


def test_append_get_roundtrip_preserves_order():
    store = SessionStore()
    store.append("s1", "Step 1: OPEN_APP {}")
    store.append("s1", "Step 2: TAP_ELEMENT {}")

    assert store.get("s1") == ["Step 1: OPEN_APP {}", "Step 2: TAP_ELEMENT {}"]


def test_get_unknown_session_returns_empty_list():
    assert SessionStore().get("missing") == []


def test_get_returns_a_copy_not_the_internal_list():
    store = SessionStore()
    store.append("s1", "Step 1: OPEN_APP {}")
    got = store.get("s1")
    got.append("mutation")

    assert store.get("s1") == ["Step 1: OPEN_APP {}"]


def test_reset_drops_the_session_trace():
    store = SessionStore()
    store.append("s1", "Step 1: OPEN_APP {}")
    store.reset("s1")

    assert store.get("s1") == []


def test_reset_unknown_session_is_a_noop():
    SessionStore().reset("never_seen")  # must not raise


def test_per_session_cap_drops_oldest_steps():
    store = SessionStore(max_steps_per_session=3)
    for i in range(1, 6):
        store.append("s1", f"Step {i}")

    # Only the newest 3 survive, in order.
    assert store.get("s1") == ["Step 3", "Step 4", "Step 5"]


def test_max_sessions_evicts_least_recently_used():
    store = SessionStore(max_sessions=2)
    store.append("a", "Step 1")
    store.append("b", "Step 1")
    # Touch "a" so "b" becomes the LRU.
    store.get("a")
    store.append("c", "Step 1")

    assert store.get("a") == ["Step 1"]
    assert store.get("c") == ["Step 1"]
    assert store.get("b") == []  # evicted


def test_ttl_eviction_prunes_idle_sessions_on_access(monkeypatch):
    import application.agents.session_store as mod

    clock = {"t": 1000.0}
    monkeypatch.setattr(mod.time, "monotonic", lambda: clock["t"])

    store = SessionStore(ttl_seconds=10.0)
    store.append("s1", "Step 1")

    # Advance past the TTL; the next access prunes the stale session.
    clock["t"] += 11.0
    assert store.get("s1") == []


def test_ttl_disabled_when_non_positive(monkeypatch):
    import application.agents.session_store as mod

    clock = {"t": 1000.0}
    monkeypatch.setattr(mod.time, "monotonic", lambda: clock["t"])

    store = SessionStore(ttl_seconds=0.0)
    store.append("s1", "Step 1")
    clock["t"] += 10_000.0

    assert store.get("s1") == ["Step 1"]
