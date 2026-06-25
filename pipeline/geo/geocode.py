"""Local NYC geocoding via Geosupport Desktop Edition (python-geosupport).

Tier-3 of the geographic unification: for datasets that have only an address
(no the_geom / lat-long / admin key), resolve a conformed geo-key set locally —
no external API, no rate limits, official NYC source (PAD/Geosupport).

Returns the same conformed keys the spatial-join tiers produce, so every table
ends up linkable to the geo dimensions:
    bbl, bin, nta2020, borough, community_district, census_tract_2020, lat, lon

Usage:
    from pipeline.geo.geocode import NYCGeocoder
    gc = NYCGeocoder()
    rec = gc.address(59, "Maiden Lane", "MN")   # -> dict or None
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Borough name/code normalization accepted by Geosupport (1=MN..5=SI).
_BORO = {
    "manhattan": "MN", "mn": "MN", "1": "MN", "new york": "MN",
    "bronx": "BX", "bx": "BX", "2": "BX",
    "brooklyn": "BK", "bk": "BK", "3": "BK", "kings": "BK",
    "queens": "QN", "qn": "QN", "4": "QN",
    "staten island": "SI", "si": "SI", "5": "SI", "richmond": "SI",
}


def _norm_boro(b: Optional[str]) -> Optional[str]:
    if not b:
        return None
    return _BORO.get(str(b).strip().lower())


class NYCGeocoder:
    """Thin wrapper over Geosupport returning a conformed geo-key dict."""

    def __init__(self):
        from geosupport import Geosupport  # imported lazily so module loads w/o engine
        self._g = Geosupport()

    @staticmethod
    def _pick(result: Dict, *keys: str) -> str:
        for k in keys:
            v = result.get(k)
            if isinstance(v, dict):
                v = v.get(k) or next((x for x in v.values() if x), "")
            if v not in (None, ""):
                return str(v).strip()
        return ""

    def _conform(self, r: Dict) -> Dict[str, Optional[str]]:
        nta = self._pick(r, "2020 Neighborhood Tabulation Area (NTA)")
        bbl = self._pick(r, "BOROUGH BLOCK LOT (BBL)")
        out = {
            "bbl": bbl or None,
            "bin": self._pick(
                r, "Building Identification Number (BIN) of Input Address or NAP",
                "Building Identification Number (BIN)") or None,
            "nta2020": nta or None,
            "borough": self._pick(r, "First Borough Name") or None,
            "community_district": self._pick(r, "COMMUNITY DISTRICT") or None,
            "census_tract_2020": self._pick(r, "2020 Census Tract") or None,
            "lat": self._pick(r, "Latitude") or None,
            "lon": self._pick(r, "Longitude") or None,
        }
        return out

    def address(self, house_number, street_name: str,
                borough: Optional[str] = None, zip_code: Optional[str] = None
                ) -> Optional[Dict[str, Optional[str]]]:
        """Geocode a single address. Returns conformed dict or None if unresolved."""
        from geosupport import GeosupportError
        kwargs = {"house_number": str(house_number or "").strip(),
                  "street_name": str(street_name or "").strip()}
        b = _norm_boro(borough)
        if b:
            kwargs["borough"] = b
        elif zip_code:
            kwargs["zip_code"] = str(zip_code).strip()
        if not kwargs["house_number"] or not kwargs["street_name"]:
            return None
        try:
            return self._conform(self._g.address(**kwargs))
        except GeosupportError as e:
            logger.debug(f"geocode miss: {kwargs} -> {e}")
            return None

    def batch(self, rows: List[Dict]) -> List[Optional[Dict]]:
        """Geocode many {house_number, street_name, borough?, zip_code?} dicts."""
        out = []
        for row in rows:
            out.append(self.address(
                row.get("house_number"), row.get("street_name"),
                row.get("borough"), row.get("zip_code")))
        return out


if __name__ == "__main__":
    gc = NYCGeocoder()
    print(gc.address(59, "Maiden Lane", "MN"))
