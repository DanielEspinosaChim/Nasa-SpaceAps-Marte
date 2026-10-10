"""Errores de API, límites de uso y dependencias compartidas."""

from __future__ import annotations

from collections import OrderedDict
from typing import Annotated

from fastapi import Depends, Path, Request

from marsmap.api.registry import RegionData

REGION_ID = Annotated[str, Path(pattern=r"^[a-z0-9_]+$", max_length=64)]


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class LruCache:
    """Caché LRU de tamaño fijo (acota la memoria aunque lleguen parámetros arbitrarios)."""

    def __init__(self, size: int):
        self.size, self._d = size, OrderedDict()

    def get(self, key):
        if key in self._d:
            self._d.move_to_end(key)
            return self._d[key]
        return None

    def put(self, key, value):
        self._d[key] = value
        self._d.move_to_end(key)
        while len(self._d) > self.size:
            self._d.popitem(last=False)

    def __len__(self):
        return len(self._d)


def client_ip(request: Request) -> str:
    # Sin confiar en X-Forwarded-For: cualquiera podría falsearlo para evadir el límite.
    return request.client.host if request.client else "unknown"


def limit_compute(request: Request) -> None:
    if not request.app.state.limiter.allow(client_ip(request)):
        raise ApiError(429, "rate_limited", "Demasiadas solicitudes; espera un minuto.")


def limit_mission(request: Request) -> None:
    if not request.app.state.mission_limiter.allow(client_ip(request)):
        raise ApiError(429, "rate_limited", "Demasiadas misiones solicitadas; espera un minuto.")


def get_region(request: Request, region_id: REGION_ID) -> RegionData:
    data = request.app.state.registry.get(region_id)
    if data is None:
        raise ApiError(404, "region_not_found", "Región no encontrada.")
    return data


RegionDep = Annotated[RegionData, Depends(get_region)]
