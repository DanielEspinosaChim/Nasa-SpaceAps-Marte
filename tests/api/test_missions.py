import pytest

from tests.api.conftest import make_client

URL = "/api/regions/jezero/missions"
FAST = {"pop_size": 20, "n_generations": 15}


def _post(client, habitat, **kw):
    return client.post(URL, json={"habitat": habitat, **FAST, **kw})


def test_pois_endpoint(client):
    fc = client.get("/api/regions/jezero/pois").json()
    assert fc["type"] == "FeatureCollection" and len(fc["features"]) >= 8
    f = fc["features"][0]
    assert f["geometry"]["type"] == "Point" and {
        "poi_id",
        "name",
        "science_value",
        "source",
    } <= set(f["properties"])


def test_mission_result_has_all_fields(client, habitat):
    r = _post(client, habitat)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {
        "result_id",
        "front",
        "named",
        "discarded",
        "params_used",
        "limitations",
        "compute_ms",
    }
    assert set(body["named"]) == {"safe", "fast", "science", "balanced"}
    ids = {m["mission_id"] for m in body["front"]}
    assert set(body["named"].values()) <= ids
    for m in body["front"]:
        assert m["geometry"]["type"] == "LineString"
        assert m["geometry"]["coordinates"][0] == m["geometry"]["coordinates"][-1]
        assert (
            len(m["legs"]) == (len(m["sequence"]) + 1 if m["sequence"] else 0) and m["explanations"]
        )
        # Un tramo puede medir 0 si el sitio cae en la misma celda de 200 m que su origen
        # (p. ej. Ha'ahóni + Atsá está a 0.1 km del aterrizaje): entonces tiene un solo punto.
        assert all(
            len(leg["coordinates"]) >= (2 if leg["distance_m"] > 0 else 1) for leg in m["legs"]
        )
        assert m["energy_wh"] <= body["params_used"]["energy_budget_wh"] + 1e-6
    assert body["limitations"]


def test_walkback_discards_are_reported(client, habitat):
    body = _post(client, habitat).json()
    far = [d for d in body["discarded"] if d["reason_code"] == "outside_walkback"]
    # Con datos reales de Mars 2020, los sitios del borde del cráter (Witch Hazel Hill, ~10.5 km)
    # quedan fuera del walkback de 10 km.
    assert far and all(d["reason_code"] == "outside_walkback" for d in far)
    assert all(d["reason"] for d in body["discarded"])


def test_same_request_hits_cache_and_select_uses_it(client, habitat):
    a = _post(client, habitat).json()
    b = _post(client, habitat).json()
    assert a["result_id"] == b["result_id"]
    for weights, key in (({"safety": 1, "science": 0, "speed": 0}, "safe"),
                         ({"safety": 0, "science": 1, "speed": 0}, "science"),
                         ({"safety": 0, "science": 0, "speed": 1}, "fast")):  # fmt: skip
        r = client.post(f"{URL}/{a['result_id']}/select", json=weights)
        assert r.status_code == 200 and r.json()["mission_id"] == a["named"][key]


def test_select_errors(client, habitat):
    rid = _post(client, habitat).json()["result_id"]
    r = client.post(f"{URL}/{'0' * 16}/select", json={"safety": 1, "science": 0, "speed": 0})
    assert r.status_code == 404 and r.json()["code"] == "result_expired"
    assert (
        client.post(
            f"{URL}/not-a-hash/select", json={"safety": 1, "science": 0, "speed": 0}
        ).status_code
        == 422
    )
    for w in (
        {"safety": 0, "science": 0, "speed": 0},
        {"safety": 2, "science": 0, "speed": 0},
        {"safety": 1},
    ):
        assert client.post(f"{URL}/{rid}/select", json=w).status_code == 422


def test_input_validation(client, habitat):
    bad = [
        {"pop_size": 5000}, {"n_generations": 100000}, {"energy_budget_wh": -1}, {"energy_budget_wh": 1e9},
        {"max_time_h": 0}, {"max_radius_m": 1e9}, {"poi_ids": ["../etc/passwd"]},
        {"poi_ids": [f"p{i}" for i in range(21)]}, {"seed": -1},
    ]  # fmt: skip
    for extra in bad:
        r = _post(client, habitat, **extra)
        assert r.status_code == 422 and r.json()["code"] == "validation_error", extra
    r = _post(client, habitat, poi_ids=["no_existe"])
    assert r.status_code == 422 and r.json()["code"] == "unknown_poi"


def test_habitat_errors(client, blocked_point):
    r = _post(client, blocked_point)
    assert r.status_code == 422 and r.json()["code"] == "habitat_blocked"
    r = _post(client, {"lat": 50, "lon": 10})
    assert r.status_code == 422 and r.json()["code"] == "out_of_region"


def test_poi_subset_and_tiny_budget(client, habitat):
    features = client.get("/api/regions/jezero/pois").json()["features"]
    ids = [f["properties"]["poi_id"] for f in features[:2]]
    body = _post(client, habitat, poi_ids=ids, energy_budget_wh=30).json()
    assert len(body["front"]) == 1 and body["front"][0]["sequence"] == []
    assert body["front"][0]["legs"] == [] and len(body["front"][0]["geometry"]["coordinates"]) == 2
    assert "vacía" in body["front"][0]["explanations"][0]


def test_mission_rate_limit_returns_429(data_dir, habitat):
    c = make_client(data_dir, mission_rate_limit_per_minute=2)
    codes = [_post(c, habitat, seed=i).status_code for i in range(4)]
    assert codes == [200, 200, 429, 429]


@pytest.mark.slow
def test_full_default_mission_under_20s(client, habitat):
    import time

    t0 = time.perf_counter()
    r = client.post(URL, json={"habitat": habitat, "seed": 7})
    assert r.status_code == 200 and time.perf_counter() - t0 < 20.0
