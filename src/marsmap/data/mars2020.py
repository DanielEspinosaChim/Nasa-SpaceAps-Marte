"""Datos reales de Mars 2020 (NASA/JPL): sitios de muestras, waypoints y recorrido del rover.

Fuente: capas públicas de «Where is Perseverance» (mars.nasa.gov/mmgis-maps/M20). Descarga solo
por https desde dominios de la lista blanca, con tope de tamaño y sin seguir redirecciones a
otros dominios. Genera `poi.geojson` de la región a partir de los sitios de muestras.

    python -m marsmap.data.mars2020 --region jezero
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from marsmap.config.regions import get_region
from marsmap.planning.mission.poi import PointOfInterest, pois_from_dicts, pois_to_geojson
from marsmap.terrain.fetch import check_url

BASE = "https://mars.nasa.gov/mmgis-maps/M20/Layers/json/"
LAYERS = {
    "samples": "M20_SAMPLE_v3.json",  # sitios de muestras (Sampling Locations)
    "waypoints": "M20_waypoints.json",  # posiciones del rover por sol
    "traverse": "M20_traverse.json",  # recorrido (para validar rutas contra el de NASA)
    "depot": "M20_TF_Sample_Depot.json",  # zona del depósito de muestras (Three Forks)
}
MAX_BYTES = 25_000_000
SAMPLES_SOURCE = "NASA/JPL Mars 2020 — Sampling Locations (M20_SAMPLE_v3.json)"


class _SameWhitelistRedirect(urllib.request.HTTPRedirectHandler):
    """Una redirección solo se sigue si el destino también está en la lista blanca."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_json(url: str, timeout: float = 60.0) -> dict:
    check_url(url)
    opener = urllib.request.build_opener(_SameWhitelistRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "mars-scout/0.1"})  # noqa: S310
    with opener.open(req, timeout=timeout) as resp:  # noqa: S310  (https + lista blanca verificados)
        raw = resp.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f"respuesta demasiado grande (> {MAX_BYTES} bytes): {url}")
    return json.loads(raw)


# --- Rúbrica de valor científico --------------------------------------------------------------
# NASA no publica un «valor científico» numérico: esta rúbrica es del proyecto y es heurística.
# Se apoya solo en lo que NASA reporta de cada muestra (tipo y litología) y premia la evidencia de
# agua y alteración acuosa, que es el objetivo de Mars 2020 en Jezero.
BASE_BY_TYPE = {"rock core": 0.70, "regolith": 0.40, "atmospheric": 0.20}
LITHOLOGY_BONUS = (  # (fragmento en minúsculas, bono); gana el mayor que coincida
    ("serpentin", 0.25),  # alteración acuosa del manto
    ("silica", 0.25),  # sílice/carbonato: agua y posible biofirma
    ("carbonate", 0.25),
    ("sedimentar", 0.20),  # sedimentos: delta y ambiente acuático
    ("mixed", 0.20),
    ("impactite", 0.10),
    ("igneous", 0.05),
)
PAIR_BONUS = 0.05  # núcleo doble (dos muestras en el mismo sitio)
DWELL_H_PER_SAMPLE = {
    "rock core": 2.0,
    "regolith": 1.5,
    "atmospheric": 0.5,
}  # supuesto del proyecto


def science_value(sample_type: str, rock_type: str, n_samples: int) -> float:
    base = BASE_BY_TYPE.get(sample_type.strip().lower(), 0.30)
    rock = rock_type.lower()
    bonus = max((b for key, b in LITHOLOGY_BONUS if key in rock), default=0.0)
    return round(min(1.0, base + bonus + (PAIR_BONUS if n_samples > 1 else 0.0)), 2)


def dwell_hours(sample_type: str, n_samples: int) -> float:
    return DWELL_H_PER_SAMPLE.get(sample_type.strip().lower(), 1.0) * max(1, n_samples)


def _slug(text: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_.lower()).strip("_") or "sitio"


def build_pois(samples: dict) -> list[PointOfInterest]:
    """Un punto de interés por cada sitio de muestra del GeoJSON de NASA."""
    items = []
    for feat in samples.get("features", []):
        p = feat.get("properties") or {}
        lon, lat = feat["geometry"]["coordinates"][:2]
        num = str(p.get("sample_num", "")).strip()
        n_samples = max(1, num.count("&") + 1) if re.search(r"\d", num) else 1
        stype, rock = str(p.get("sample_type", "")), str(p.get("rock_type", ""))
        where = str(p.get("sample_location", "")).strip()
        name = str(p.get("sample_name", "")).strip() or str(p.get("outcrop_name", "")).strip()
        sampled = str(p.get("sol", "")).strip().upper() != "TBD"
        value = science_value(stype, rock, n_samples)
        items.append(
            {
                "poi_id": f"s{_slug(num or 'x')}_{_slug(name)}",
                "name": f"{name} ({where})" if where else name,
                "lat": lat,
                "lon": lon,
                "science_value": value,
                "dwell_time_h": min(12.0, dwell_hours(stype, n_samples)),
                "category": _slug(where) or "other",
                "rationale": (
                    f"{'Muestra tomada' if sampled else 'Muestra prevista'} por Perseverance en "
                    f"{where or 'Jezero'} ({stype or 'tipo n/d'}; litología según NASA: "
                    f"{rock or 'n/d'}). Valor científico {value:.2f} por la rúbrica del proyecto "
                    "(tipo de muestra + litología), no por un dato de NASA."
                ),
                "source": SAMPLES_SOURCE,
                "sol": str(p.get("sol", "")).strip(),
                "location": where,
                "sample_type": stype,
                "rock_type": rock,
            }
        )
    return pois_from_dicts(items)


def landing_site(waypoints: dict) -> tuple[float, float]:
    """(lat, lon) del primer waypoint (sol 13): posición de aterrizaje publicada por NASA."""
    first = min(waypoints["features"], key=lambda f: f["properties"]["sol"])
    return first["properties"]["lat"], first["properties"]["lon"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--region", required=True)
    ap.add_argument("--raw-dir", type=Path)
    ap.add_argument("--out", type=Path, help="carpeta data/processed/<región>")
    a = ap.parse_args(argv)
    try:
        region = get_region(a.region)
        raw = a.raw_dir or Path("data/raw") / region.region_id / "mars2020"
        out = a.out or Path("data/processed") / region.region_id
        raw.mkdir(parents=True, exist_ok=True)
        out.mkdir(parents=True, exist_ok=True)
        data = {}
        for key, fname in LAYERS.items():
            data[key] = fetch_json(BASE + fname)
            (raw / fname).write_text(json.dumps(data[key], ensure_ascii=False), encoding="utf-8")
            print(f"  {fname}: {len(data[key].get('features', []))} elementos")
        pois = build_pois(data["samples"])
        lon_min, lat_min, lon_max, lat_max = region.bbox
        inside = [p for p in pois if lon_min <= p.lon <= lon_max and lat_min <= p.lat <= lat_max]
        meta = {
            "name": "Sitios de muestras de Mars 2020 como puntos de interés",
            "source": SAMPLES_SOURCE,
            "retrieved_at": datetime.now(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "science_value_note": "Rúbrica del proyecto (tipo de muestra + litología), no un dato de NASA.",
            "landing_site": dict(zip(("lat", "lon"), landing_site(data["waypoints"]), strict=True)),
        }
        (out / "poi.geojson").write_text(
            json.dumps(pois_to_geojson(inside, meta), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except (KeyError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"{len(inside)} puntos de interés reales → {out / 'poi.geojson'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
