"""
ors.py — Ruteo por calles reales con OpenRouteService (OSM).

Dibuja el camino que sigue las calles, en el orden de entrega. El plan gratuito
permite hasta 50 puntos por petición, así que troceamos la ruta y unimos los
tramos. Requiere una clave gratuita de https://openrouteservice.org
(cuenta en https://account.heigit.org).
"""
from __future__ import annotations
import math
import time
import requests

ORS_URL = "https://api.openrouteservice.org/v2/directions/{profile}/geojson"
MAX_WP = 50  # tope de puntos por petición en el plan gratuito


def circle_polygon(lat, lon, radius_m=120, n=16):
    """Anillo (lon,lat) que aproxima un círculo de radius_m alrededor del punto."""
    dlat = radius_m / 111320.0
    dlon = radius_m / (111320.0 * max(math.cos(math.radians(lat)), 1e-6))
    ring = [[lon + dlon * math.cos(2 * math.pi * k / n),
             lat + dlat * math.sin(2 * math.pi * k / n)] for k in range(n + 1)]
    return ring


def to_multipolygon(circles):
    """Convierte una lista de anillos en un GeoJSON MultiPolygon (o None)."""
    if not circles:
        return None
    return {"type": "MultiPolygon", "coordinates": [[c] for c in circles]}


def _chunk_ranges(n: int, size: int = MAX_WP):
    """Divide n puntos en tramos de <=size, solapando 1 punto para que unan."""
    if n <= size:
        return [(0, n)]
    ranges, start = [], 0
    while start < n - 1:
        end = min(start + size, n)
        ranges.append((start, end))
        if end >= n:
            break
        start = end - 1  # el último punto de un tramo es el primero del siguiente
    return ranges


def route_geometry(coords_latlon, api_key, profile="driving-car",
                   avoid=None, pause=1.2, timeout=40):
    """
    coords_latlon: lista de (lat, lon) EN ORDEN DE VISITA.
    avoid: GeoJSON (MultiPolygon/Polygon) de zonas a esquivar, o None.
    Devuelve dict:
      {'geometry': [(lat,lon), ...], 'distance_m': float, 'duration_s': float}
      o {'error': '...'} si algo falla.
    """
    if not api_key or len(coords_latlon) < 2:
        return None

    headers = {"Authorization": api_key.strip(), "Content-Type": "application/json"}
    url = ORS_URL.format(profile=profile)
    geom, dist, dur = [], 0.0, 0.0
    ranges = _chunk_ranges(len(coords_latlon))

    for i, (s, e) in enumerate(ranges):
        seg = coords_latlon[s:e]
        body = {"coordinates": [[lon, lat] for lat, lon in seg]}  # ORS usa lon,lat
        if avoid:
            body["options"] = {"avoid_polygons": avoid}
        try:
            r = requests.post(url, json=body, headers=headers, timeout=timeout)
            if r.status_code == 401:
                return {"error": "Clave de OpenRouteService inválida (401)."}
            if r.status_code == 429:
                return {"error": "Límite de peticiones alcanzado (429). Prueba más tarde."}
            r.raise_for_status()
            feat = r.json()["features"][0]
            pts = [(c[1], c[0]) for c in feat["geometry"]["coordinates"]]  # a lat,lon
            if geom and pts:
                pts = pts[1:]  # evitar duplicar el punto de unión
            geom.extend(pts)
            summ = feat["properties"].get("summary", {})
            dist += summ.get("distance", 0.0)
            dur += summ.get("duration", 0.0)
        except Exception as ex:  # noqa: BLE001
            return {"error": f"No se pudo trazar la ruta: {ex}"}
        if i < len(ranges) - 1:
            time.sleep(pause)  # respetar el ritmo del servicio gratuito

    return {"geometry": geom, "distance_m": dist, "duration_s": dur}
