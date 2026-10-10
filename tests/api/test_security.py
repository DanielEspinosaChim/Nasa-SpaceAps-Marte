import pytest

from marsmap.api.deps import LruCache
from marsmap.api.ratelimit import RateLimiter
from tests.api.conftest import make_client

BAD_IDS = [
    "..%2F..%2Fetc%2Fpasswd",
    "..",
    "JEZERO",
    "jezero;ls",
    "jezero%00",
    "no_existe",
    "a" * 200,
]


@pytest.mark.parametrize("bad", BAD_IDS)
def test_region_id_traversal_and_garbage_rejected(client, bad):
    for path in (f"/api/regions/{bad}/layers", f"/api/regions/{bad}/cell?lat=1&lon=1"):
        r = client.get(path)
        assert r.status_code in (404, 422)
        assert set(r.json()) == {"error", "code"}
        assert "Traceback" not in r.text and "passwd" not in r.json()["error"]


@pytest.mark.parametrize("bad", BAD_IDS + ["missing_layer"])
def test_layer_id_never_reads_outside_whitelist(client, bad):
    r = client.get(f"/api/regions/jezero/layers/{bad}/image")
    assert r.status_code in (404, 422) and set(r.json()) == {"error", "code"}


def test_unhandled_exception_returns_generic_500(data_dir):
    c = make_client(data_dir)

    def boom(*a, **k):
        raise RuntimeError("secreto-interno /etc/passwd")

    c.app.state.registry.get = boom
    r = c.get("/api/regions/jezero/layers")
    assert r.status_code == 500
    assert r.json() == {"error": "Error interno del servidor.", "code": "internal_error"}


def test_validation_errors_do_not_echo_input(client):
    r = client.post(
        "/api/regions/jezero/route", json={"start": {"lat": "<script>alert(1)</script>", "lon": 1}}
    )
    assert r.status_code == 422 and "<script>" not in r.text


def test_cors_only_for_configured_origins(client):
    ok = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    bad = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers


def test_rate_limiter_window_and_independent_ips():
    t = [0.0]
    rl = RateLimiter(3, clock=lambda: t[0])
    assert [rl.allow("a") for _ in range(4)] == [True, True, True, False]
    assert rl.allow("b")
    t[0] = 61.0
    assert rl.allow("a")


def test_lru_cache_is_bounded():
    c = LruCache(3)
    for i in range(50):
        c.put(i, i)
    assert len(c) == 3 and c.get(49) == 49 and c.get(0) is None


def test_endpoint_rate_limit_returns_429(data_dir, free_points):
    c = make_client(data_dir, rate_limit_per_minute=2)
    body = {"start": free_points[0], "goal": free_points[1], "preset": "fast"}
    codes = [c.post("/api/regions/jezero/route", json=body).status_code for _ in range(4)]
    assert codes[2:] == [429, 429] and 429 not in codes[:2]
    assert c.post("/api/regions/jezero/route", json=body).json()["code"] == "rate_limited"
    assert c.get("/api/health").status_code == 200  # solo se limitan los endpoints de cómputo
