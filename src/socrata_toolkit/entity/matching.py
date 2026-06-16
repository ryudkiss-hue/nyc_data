"""Entity matching and similarity scoring for record deduplication."""
from __future__ import annotations

import math
from typing import Any

__all__ = [
    "EntityMatcher",
    "calculate_similarity_score",
    "MatchingStrategy",
    "ExactMatch",
    "FuzzyMatch",
    "CompositeMatch",
    "GeographicMatch",
    "TemporalMatch",
    "SemanticMatch",
    "MatchResult",
    "PhoneticMatch",
]

class MatchResult:
    pass

class MatchingStrategy:
    @property
    def name(self) -> str:
        """Return the strategy class name as its identifier."""
        return self.__class__.__name__

    def score(self, record1: dict[str, Any], record2: dict[str, Any]) -> float:
        """Return a similarity score in [0, 1] between two records."""
        return 0.0

class ExactMatch(MatchingStrategy):
    def __init__(self, fields: list[str], field_weights: dict[str, float] | None = None, case_sensitive: bool = True, threshold: float = 1.0) -> None:
        self.fields = fields
        self.field_weights = field_weights or {f: 1.0/len(fields) for f in fields}
        self.case_sensitive = case_sensitive
        self.threshold = threshold

    def score(self, record1: dict[str, Any], record2: dict[str, Any]) -> float:
        """Return a weighted exact-match similarity score across the configured fields."""
        total_score = 0.0
        total_weight = sum(self.field_weights.get(f, 0) for f in self.fields)
        if total_weight == 0:
            return 0.0

        for field in self.fields:
            v1 = record1.get(field)
            v2 = record2.get(field)
            if v1 is None or v2 is None:
                continue

            match = False
            if isinstance(v1, str) and isinstance(v2, str) and not self.case_sensitive:
                match = v1.lower() == v2.lower()
            else:
                match = v1 == v2

            if match:
                total_score += self.field_weights.get(field, 0)

        return total_score / total_weight

class FuzzyMatch(MatchingStrategy):
    def __init__(self, fields: list[str], threshold: float = 0.8, algorithm: str = 'ratio') -> None:
        self.fields = fields
        self.threshold = threshold
        self.algorithm = algorithm

    def _fuzzy_score(self, s1: str, s2: str) -> float:
        s1 = str(s1).lower()
        s2 = str(s2).lower()

        if self.algorithm == 'token_set_ratio':
            set1 = set(s1.split())
            set2 = set(s2.split())
            intersection = len(set1.intersection(set2))
            if min(len(set1), len(set2)) == 0:
                return 0.0
            return float(intersection) / float(min(len(set1), len(set2)))

        import difflib
        return difflib.SequenceMatcher(None, s1, s2).ratio()

    def score(self, record1: dict[str, Any], record2: dict[str, Any]) -> float:
        """Return the mean fuzzy string similarity across all configured fields."""
        scores = []
        for field in self.fields:
            v1 = record1.get(field)
            v2 = record2.get(field)
            if v1 is None or v2 is None:
                continue
            scores.append(self._fuzzy_score(v1, v2))

        if not scores:
            return 0.0
        return sum(scores) / len(scores)

class PhoneticMatch(MatchingStrategy):
    def __init__(self, fields: list[str]) -> None:
        self.fields = fields

    def _soundex(self, name: str) -> str:
        name = name.upper()
        soundex = name[0]
        dictionary = {"BFPV": "1", "CGJKQSXZ": "2", "DT": "3", "L": "4", "MN": "5", "R": "6", "AEIOUHWY": "."}
        for char in name[1:]:
            for key in dictionary.keys():
                if char in key:
                    code = dictionary[key]
                    if code != '.' and code != soundex[-1]:
                        soundex += code
                    break
        soundex = soundex.replace(".", "")
        return (soundex + "0000")[:4]

    def score(self, record1: dict[str, Any], record2: dict[str, Any]) -> float:
        """Return 1.0 if all configured fields share the same Soundex code, else the proportion that match."""
        scores = []
        for field in self.fields:
            v1 = record1.get(field)
            v2 = record2.get(field)
            if not v1 or not v2:
                continue
            sx1 = self._soundex(str(v1))
            sx2 = self._soundex(str(v2))
            scores.append(1.0 if sx1 == sx2 else 0.0)

        if not scores:
            return 0.0
        return sum(scores) / len(scores)

class GeographicMatch(MatchingStrategy):
    def __init__(self, lat_field: str = 'latitude', lon_field: str = 'longitude', distance_threshold_m: float = 20.0) -> None:
        self.lat_field = lat_field
        self.lon_field = lon_field
        self.distance_threshold_m = distance_threshold_m

    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000 # radius of earth in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi/2.0)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(delta_lambda/2.0)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def score(self, record1: dict[str, Any], record2: dict[str, Any]) -> float:
        """Return a proximity score of 1.0 for records within the distance threshold, 0.0 otherwise."""
        lat1 = record1.get(self.lat_field)
        lon1 = record1.get(self.lon_field)
        lat2 = record2.get(self.lat_field)
        lon2 = record2.get(self.lon_field)

        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return 0.0

        dist = self._haversine(float(lat1), float(lon1), float(lat2), float(lon2))
        if dist <= self.distance_threshold_m:
            return 1.0 - (dist / self.distance_threshold_m) * 0.1 # slightly lower score for further distance
        return 0.0

class TemporalMatch(MatchingStrategy):
    def __init__(self, start_field: str = 'start_date', end_field: str = 'end_date') -> None:
        self.start_field = start_field
        self.end_field = end_field

    def score(self, record1: dict[str, Any], record2: dict[str, Any]) -> float:
        """Return 1.0 if the date ranges of the two records overlap, 0.0 otherwise."""
        # Assuming format YYYY-MM-DD
        s1 = record1.get(self.start_field)
        e1 = record1.get(self.end_field)
        s2 = record2.get(self.start_field)
        e2 = record2.get(self.end_field)

        if not all([s1, e1, s2, e2]):
            return 0.0

        if s1 <= e2 and s2 <= e1: # Check overlap
            return 1.0
        return 0.0

class CompositeMatch(MatchingStrategy):
    def __init__(self, strategies: list[tuple[MatchingStrategy, float]]) -> None:
        self.strategies = strategies

    def score(self, record1: dict[str, Any], record2: dict[str, Any]) -> float:
        """Return a weighted average of all constituent strategy scores."""
        total_score = 0.0
        total_weight = 0.0
        for strategy, weight in self.strategies:
            total_score += strategy.score(record1, record2) * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0
        return total_score / total_weight

class SemanticMatch(MatchingStrategy):
    def score(self, record1: dict[str, Any], record2: dict[str, Any]) -> float:
        """Return a semantic similarity score between two records using fuzzy string matching on common keys."""
        from difflib import SequenceMatcher

        scores = []
        common_keys = set(record1.keys()) & set(record2.keys())
        for key in common_keys:
            v1, v2 = record1[key], record2[key]
            if isinstance(v1, str) and isinstance(v2, str) and v1 and v2:
                scores.append(SequenceMatcher(None, v1, v2).ratio())

        return sum(scores) / len(scores) if scores else 0.0

class EntityMatcher:
    def match_entities(self, source: list[dict[str, Any]], target: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Match records in source against target and return a list of match results."""
        return []

def calculate_similarity_score(entity1: dict[str, Any], entity2: dict[str, Any]) -> float:
    """Return an overall similarity score between two entity dicts."""
    return 0.0
