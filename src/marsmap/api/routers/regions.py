"""Regiones, capas, imágenes y consulta de celda (feature 002)."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response

from marsmap.api import render
from marsmap.api.deps import ApiError, RegionDep
from marsmap.api.schemas import CellOut, LayerOut, RegionOut
from marsmap.geo.coords import lonlat_to_rowcol, normalize_lon

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/regions", response_model=list[RegionOut])
def list_regions(request: Request) -> list[RegionOut]:
    return [
        RegionOut(
            region_id=d.region.region_id,
            name=d.region.name,
            bbox=list(d.region.bbox),
            description=d.region.description,
        )
        for d in request.app.state.registry.regions.values()
    ]


@lru_cache(maxsize=64)
def _legend(layer_id: str, path: str) -> tuple:
    return tuple(render.legend(layer_id, path))


@router.get("/regions/{region_id}/layers", response_model=list[LayerOut])
def list_layers(region: RegionDep) -> list[LayerOut]:
    out = []
    for lid, meta in region.layers.items():
        out.append(
            LayerOut(
                **meta.model_dump(exclude={"file", "bbox"}),
                bbox=list(meta.bbox),
                legend=list(_legend(lid, str(region.layer_files[lid]))),
                image_url=f"/api/regions/{region.region.region_id}/layers/{lid}/image",
            )
        )
    return out


@lru_cache(maxsize=32)
def _png(layer_id: str, path: str, mtime: float) -> bytes:  # mtime invalida la caché al regenerar
    return render.render_png(layer_id, path)


@router.get("/regions/{region_id}/layers/{layer_id}/image")
def layer_image(
    region: RegionDep, layer_id: Annotated[str, Path(pattern=r"^[a-z_]+$", max_length=64)]
):
    f = region.layer_files.get(
        layer_id
    )  # solo la lista blanca: nunca se concatena layer_id a una ruta
    if f is None:
        raise ApiError(404, "layer_not_found", "Capa no encontrada.")
    return Response(
        _png(layer_id, str(f), f.stat().st_mtime),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/regions/{region_id}/cell", response_model=CellOut)
def cell(
    region: RegionDep,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=360)],
) -> CellOut:
    grid = region.grid
    lon = normalize_lon(lon)
    row, col = lonlat_to_rowcol(grid.transform, lon, lat)
    h, w = grid.shape
    if not (0 <= row < h and 0 <= col < w):
        raise ApiError(422, "out_of_region", "La coordenada está fuera de la región.")

    def val(layer_id: str):
        f = region.layer_files.get(layer_id)
        if f is None:
            return None
        v, _ = render.sample(f, row, col)
        return None if render.is_nodata(layer_id, v) else float(v)

    trav = val("traversability")
    return CellOut(
        lat=lat,
        lon=lon,
        elevation_m=val("elevation"),
        slope_deg=val("slope"),
        roughness_m=val("roughness"),
        traversability=None if trav is None else int(trav),
    )
