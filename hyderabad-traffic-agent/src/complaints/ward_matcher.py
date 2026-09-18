from typing import Optional, Dict, Any
from src.utils.geo_utils import match_coordinates_to_ward, is_point_in_hyderabad
from src.complaints.classifier import ComplaintClassifier

class WardMatcher:
    """
    Spatial lookup matcher: maps GPS coordinates or textual descriptions
    to GHMC Ward IDs.
    """

    def __init__(self):
        self.classifier = ComplaintClassifier()

    def resolve_ward(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        location_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolves ward from GPS coordinates or textual landmark.
        """
        # 1. Try GPS Spatial Match
        if lat is not None and lon is not None:
            if is_point_in_hyderabad(lat, lon):
                matched = match_coordinates_to_ward(lat, lon)
                if matched:
                    return {
                        "ward_id": matched.get("id"),
                        "ward_name": matched.get("name"),
                        "match_method": "GPS_POLYGON_MATCH",
                        "confidence": 0.98
                    }

        # 2. Try Landmark Text Match
        if location_text:
            classified = self.classifier.classify_complaint(location_text)
            if classified.get("inferred_ward_id"):
                w_id = classified["inferred_ward_id"]
                name_map = {
                    1: "Ameerpet", 2: "Gachibowli", 3: "Kukatpally", 4: "Secunderabad",
                    5: "Madhapur", 6: "Banjara Hills", 7: "Jubilee Hills",
                    8: "Begumpet", 9: "Uppal", 10: "Dilsukhnagar"
                }
                return {
                    "ward_id": w_id,
                    "ward_name": name_map.get(w_id, "Unknown"),
                    "match_method": "LANDMARK_TEXT_MATCH",
                    "confidence": 0.85
                }

        # 3. Default fallback to Gachibowli (Ward 2)
        return {
            "ward_id": 2,
            "ward_name": "Gachibowli",
            "match_method": "DEFAULT_FALLBACK",
            "confidence": 0.50
        }
