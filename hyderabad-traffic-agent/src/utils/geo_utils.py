import json
import math
from pathlib import Path
from typing import Optional, Dict, Any, List

HYDERABAD_BBOX = {
    "min_lat": 17.20,
    "max_lat": 17.60,
    "min_lon": 78.25,
    "max_lon": 78.65
}

def is_point_in_hyderabad(lat: float, lon: float) -> bool:
    """Checks if coordinates fall within the Hyderabad bounding box."""
    return (
        HYDERABAD_BBOX["min_lat"] <= lat <= HYDERABAD_BBOX["max_lat"] and
        HYDERABAD_BBOX["min_lon"] <= lon <= HYDERABAD_BBOX["max_lon"]
    )

def point_in_polygon(x: float, y: float, polygon: List[List[float]]) -> bool:
    """
    Ray-casting algorithm to determine if point (x, y) = (lon, lat) is inside polygon.
    polygon is a list of [lon, lat] points.
    """
    inside = False
    n = len(polygon)
    if n < 3:
        return False

    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def match_coordinates_to_ward(lat: float, lon: float, geojson_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Matches lat/lon to a GHMC ward polygon.
    Returns matched ward dictionary or None.
    """
    if not is_point_in_hyderabad(lat, lon):
        return None

    if geojson_path is None:
        geojson_path = str(Path(__file__).resolve().parent.parent.parent / "data" / "geo" / "ghmc_wards.geojson")

    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for feature in data.get("features", []):
            geometry = feature.get("geometry", {})
            geom_type = geometry.get("type")
            coords = geometry.get("coordinates", [])

            if geom_type == "Polygon" and coords:
                exterior = coords[0]
                if point_in_polygon(lon, lat, exterior):
                    return feature.get("properties", {})
            elif geom_type == "MultiPolygon" and coords:
                for poly in coords:
                    if poly and point_in_polygon(lon, lat, poly[0]):
                        return feature.get("properties", {})
    except Exception:
        pass

    return None

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two points in kilometers."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c
