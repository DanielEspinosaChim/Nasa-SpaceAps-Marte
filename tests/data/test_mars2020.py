"""Tests sin red del módulo de datos reales de Mars 2020 (formato del GeoJSON de NASA)."""

import io
import json

import pytest

from marsmap.data import mars2020
from marsmap.data.mars2020 import build_pois, dwell_hours, landing_site, science_value


def feat(num, name, where, stype, rock, lon=77.45, lat=18.44, sol="100"):
    return {
        "type": "Feature",
        "properties": {
            "sample_num": num,
            "sol": sol,
            "sample_name": name,
            "outcrop_name": name,
            "sample_location": where,
            "sample_type": stype,
            "rock_type": rock,
        },
        "geometry": {"type": "Point", "coordinates": [lon, lat, -2570.0]},
    }


SAMPLES = {
    "features": [
        feat("1", "Roubion", "Polygon Valley", "Atmospheric", "n/a"),
        feat("2 & 3", "Montdenier + Montagnac", "Artuby Ridge", "Rock Core", "Igneous"),
        feat("10 & 11", "Swift Run + Skyland", "Fan Front", "Rock Core", "Sedimentary"),
        feat("24", "Comet Geyser", "Margin", "Rock Core", "Silica-cemented Carbonate"),
        feat("27", "Green Gardens", "Crater Rim", "Rock Core", "Serpentinite"),
        feat("TBD", "Gallants", "Crater Rim", "Rock Core", "Igneous or Sedimentary", sol="TBD"),
        feat("25", "Sapphire_Canyon", "Neretva Vallis", "Rock Core", "Sedimentary"),
        feat("4 & 5", "Ha'ahóni + Atsá", "Octavia E. Butler", "Rock Core", "Igneous"),
    ]
}


def test_pois_have_valid_unique_ids_and_real_fields():
    pois = build_pois(SAMPLES)
    assert len(pois) == len(SAMPLES["features"])
    ids = [p.poi_id for p in pois]
    assert len(ids) == len(set(ids))
    assert all(i.isascii() and i.replace("_", "").isalnum() for i in ids)
    assert "s25_sapphire_canyon" in ids and "s4_5_ha_ahoni_atsa" in ids
    swift = next(p for p in pois if p.poi_id.startswith("s10_11"))
    assert swift.sol == "100" and swift.rock_type == "Sedimentary" and swift.location == "Fan Front"
    assert all(p.source.startswith("NASA/JPL Mars 2020") for p in pois)
    assert all(0 <= p.science_value <= 1 and 0 < p.dwell_time_h <= 12 for p in pois)


def test_rubric_orders_sites_by_evidence_of_water():
    v = {
        "atm": science_value("Atmospheric", "n/a", 1),
        "igneous": science_value("Rock Core", "Igneous", 1),
        "sed": science_value("Rock Core", "Sedimentary", 1),
        "serp": science_value("Rock Core", "Serpentinite", 1),
        "carb": science_value("Rock Core", "Silica-cemented Carbonate", 1),
    }
    assert v["atm"] < v["igneous"] < v["sed"] < v["serp"] == v["carb"] <= 1.0
    assert science_value("Rock Core", "Igneous", 2) > science_value("Rock Core", "Igneous", 1)
    assert science_value("Algo raro", "???", 1) == 0.30  # tipo desconocido: valor base prudente


def test_dwell_scales_with_samples_and_is_capped():
    assert dwell_hours("Rock Core", 2) == 4.0 and dwell_hours("Atmospheric", 1) == 0.5
    pois = build_pois(
        {"features": [feat("1 & 2 & 3 & 4 & 5 & 6 & 7", "X", "Y", "Rock Core", "Igneous")]}
    )
    assert pois[0].dwell_time_h == 12.0  # el modelo de POI acota la estancia


def test_unsampled_target_is_labeled_as_planned():
    gallants = next(p for p in build_pois(SAMPLES) if "gallants" in p.poi_id)
    assert gallants.sol == "TBD" and "prevista" in gallants.rationale


def test_rationale_states_the_value_is_not_a_nasa_number():
    assert all("no por un dato de NASA" in p.rationale for p in build_pois(SAMPLES))


def test_landing_site_is_first_waypoint():
    wp = {
        "features": [
            {"properties": {"sol": 40, "lat": 18.5, "lon": 77.4}},
            {"properties": {"sol": 13, "lat": 18.44462715, "lon": 77.45088572}},
        ]
    }
    assert landing_site(wp) == (18.44462715, 77.45088572)


@pytest.mark.parametrize(
    "url", ["http://mars.nasa.gov/x.json", "https://evil.example.com/x.json", "file:///etc/passwd"]
)
def test_fetch_rejects_non_whitelisted_urls_before_any_request(url, monkeypatch):
    monkeypatch.setattr(
        mars2020.urllib.request, "build_opener", lambda *a: pytest.fail("no debe abrir conexión")
    )
    with pytest.raises(ValueError):
        mars2020.fetch_json(url)


def test_redirect_to_other_domain_is_blocked():
    handler = mars2020._SameWhitelistRedirect()  # noqa: SLF001
    with pytest.raises(ValueError):
        handler.redirect_request(None, None, 302, "Found", {}, "https://evil.example.com/a.json")


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _fake_opener(payload: bytes):
    class Opener:
        def open(self, req, timeout=None):
            return _Resp(payload)

    return lambda *a: Opener()


def test_fetch_parses_json_and_enforces_size_cap(monkeypatch):
    url = mars2020.BASE + "M20_SAMPLE_v3.json"
    monkeypatch.setattr(mars2020.urllib.request, "build_opener", _fake_opener(b'{"ok": 1}'))
    assert mars2020.fetch_json(url) == {"ok": 1}
    monkeypatch.setattr(mars2020, "MAX_BYTES", 5)
    monkeypatch.setattr(mars2020.urllib.request, "build_opener", _fake_opener(b"x" * 50))
    with pytest.raises(ValueError, match="demasiado grande"):
        mars2020.fetch_json(url)


def test_cli_writes_pois_and_raw_files(tmp_path, monkeypatch):
    waypoints = {"features": [{"properties": {"sol": 13, "lat": 18.4446, "lon": 77.4509}}]}
    layers = {
        "M20_SAMPLE_v3.json": SAMPLES,
        "M20_waypoints.json": waypoints,
        "M20_traverse.json": {"features": []},
        "M20_TF_Sample_Depot.json": {"features": []},
    }
    monkeypatch.setattr(mars2020, "fetch_json", lambda url: layers[url.rsplit("/", 1)[1]])
    raw, out = tmp_path / "raw", tmp_path / "out"
    assert mars2020.main(["--region", "jezero", "--raw-dir", str(raw), "--out", str(out)]) == 0
    data = json.loads((out / "poi.geojson").read_text(encoding="utf-8"))
    assert data["landing_site"] == {"lat": 18.4446, "lon": 77.4509}
    assert len(data["features"]) == len(SAMPLES["features"])
    assert (raw / "M20_SAMPLE_v3.json").is_file() and "rúbrica" in data[
        "science_value_note"
    ].lower()


def test_cli_rejects_unknown_region(tmp_path):
    assert (
        mars2020.main(["--region", "../etc", "--raw-dir", str(tmp_path), "--out", str(tmp_path)])
        == 2
    )
