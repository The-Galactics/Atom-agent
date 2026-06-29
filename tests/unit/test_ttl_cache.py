from infrastructure.cache.ttl_cache import TtlCache


def test_hit_within_ttl():
    t = [100.0]
    c = TtlCache(ttl_seconds=30, clock=lambda: t[0])
    c.put("u1", {"x": 1})
    t[0] = 120.0  # +20s, within TTL
    assert c.get("u1") == {"x": 1}


def test_miss_after_ttl():
    t = [100.0]
    c = TtlCache(ttl_seconds=30, clock=lambda: t[0])
    c.put("u1", {"x": 1})
    t[0] = 131.0  # +31s, expired
    assert c.get("u1") is None


def test_invalidate_drops_entry():
    c = TtlCache(ttl_seconds=30, clock=lambda: 0.0)
    c.put("u1", 1)
    c.invalidate("u1")
    assert c.get("u1") is None


def test_absent_key_returns_none():
    assert TtlCache(ttl_seconds=30).get("nope") is None
