import shutil
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from marsmap.api.main import create_app
from marsmap.api.settings import Settings
from marsmap.terrain.build import build

REPO_DATA = Path(__file__).resolve().parents[2] / "data" / "processed" / "jezero"


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("processed")
    build("jezero", d, synthetic=True, seed=42)
    for name in ("poi.geojson", "forbidden_zones.geojson"):
        shutil.copy2(REPO_DATA / name, d / "jezero" / name)
    return d


def make_client(data_dir, **kw):
    defaults = {"rate_limit_per_minute": 10_000, "mission_rate_limit_per_minute": 10_000}
    settings = Settings(data_dir=data_dir, **(defaults | kw))
    return TestClient(create_app(settings), raise_server_exceptions=False)


@pytest.fixture(scope="session")
def client(data_dir):
    return make_client(data_dir)


@pytest.fixture(scope="session")
def grid(client):
    return client.app.state.registry.get("jezero").grid


def _cells(grid, trav_value, n=1):
    rr, cc = np.nonzero(grid.traversability == trav_value)
    out = []
    for r, c in zip(
        rr[:: max(1, len(rr) // (n * 7))][:n], cc[:: max(1, len(rr) // (n * 7))][:n], strict=False
    ):
        lon, lat = grid.to_lonlat(int(r), int(c))
        out.append({"lat": lat, "lon": lon})
    return out


@pytest.fixture(scope="session")
def free_points(grid):
    """Puntos en celdas seguras conectadas entre sí (cerca del centro del terreno)."""
    pts = _cells(grid, 0, 40)
    return pts


@pytest.fixture(scope="session")
def blocked_point(grid):
    return _cells(grid, 2, 1)[0]


@pytest.fixture(scope="session")
def habitat(grid):
    """Celda segura más cercana al sitio de aterrizaje (18.444 N, 77.451 E)."""
    lat, lon = grid.cell_centers()
    d = np.hypot(lat - 18.444, lon - 77.451) + np.where(grid.traversability == 0, 0, 1e3)
    r, c = np.unravel_index(np.argmin(d), d.shape)
    lo, la = grid.to_lonlat(int(r), int(c))
    return {"lat": la, "lon": lo}
