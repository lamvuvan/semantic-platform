import time

from agents.retrieval.cache import CacheKey, ContextCache


def test_cache_get_set_in_memory():
    cache = ContextCache()
    key = CacheKey(intent="search_product", entity_ids=("p1",), params=(("k", 5),))
    assert cache.get(key) is None
    cache.set(key, {"hello": "world"}, ttl_seconds=60)
    assert cache.get(key) == {"hello": "world"}


def test_cache_expiry_in_memory():
    cache = ContextCache()
    key = CacheKey(intent="x", entity_ids=(), params=())
    cache.set(key, {"v": 1}, ttl_seconds=0)
    time.sleep(0.01)
    assert cache.get(key) is None


def test_cache_key_fingerprint_stable():
    a = CacheKey(intent="i", entity_ids=("a", "b"), params=(("x", 1),))
    b = CacheKey(intent="i", entity_ids=("a", "b"), params=(("x", 1),))
    assert a.fingerprint() == b.fingerprint()
