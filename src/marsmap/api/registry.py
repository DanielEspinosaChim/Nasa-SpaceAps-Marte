"""Lista blanca de regiones y capas cargada al arrancar. Nunca se arma una ruta con texto del cliente."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from marsmap.config.regions import Region, load_regions
from marsmap.planning.constraints import load_forbidden_zones
from marsmap.planning.mission.poi import PointOfInterest, load_pois
from marsmap.planning.terrain_grid import TerrainGrid, load_grid
from marsmap.terrain.metadata import LayerMetadata, read_metadata

log = logging.getLogger("marsmap.registry")


@dataclass
class RegionData:
    region: Region
    folder: Path
    layers: dict[str, LayerMetadata]
    layer_files: dict[str, Path]
    _grid: TerrainGrid | None = None
    pois: list[PointOfInterest] = field(default_factory=list)
    zones: list[dict] = field(default_factory=list)

    @property
    def grid(self) -> TerrainGrid:
        if self._grid is None:
            self._grid = load_grid(self.folder)
        return self._grid


class Registry:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.regions: dict[str, RegionData] = {}
        for region_id, region in load_regions().items():
            folder = data_dir / region_id
            try:
                meta = read_metadata(folder)
            except (FileNotFoundError, ValueError) as exc:
                log.warning("región %s sin capas procesadas (%s): se omite", region_id, exc)
                continue
            layers, files = {}, {}
            for layer in meta.layers:
                f = folder / layer.file
                if f.is_file():
                    layers[layer.layer_id], files[layer.layer_id] = layer, f
                else:
                    log.warning(
                        "capa %s/%s declarada pero ausente en disco", region_id, layer.layer_id
                    )
            self.regions[region_id] = RegionData(
                region, folder, layers, files,
                pois=load_pois(folder / "poi.geojson"),
                zones=load_forbidden_zones(folder / "forbidden_zones.geojson"),
            )  # fmt: skip

    def get(self, region_id: str) -> RegionData | None:
        return self.regions.get(region_id)
