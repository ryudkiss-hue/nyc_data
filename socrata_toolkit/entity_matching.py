"""
Entity matching strategies for record deduplication.

This module provides a comprehensive set of matching strategies to identify
potential duplicate records based on various attributes and algorithms.
Strategies include exact matching, fuzzy string matching, phonetic matching,
geographic proximity, temporal overlaps, and semantic similarity.

Example:
    >>> from socrata_toolkit.entity_matching import ExactMatch, FuzzyMatch
    >>> exact = ExactMatch(fields=['block_id'], threshold=1.0)
    >>> fuzzy = FuzzyMatch(fields=['address'], threshold=0.85)
    >>> score1 = exact.score({'block_id': '100'}, {'block_id': '100'})
    >>> score2 = fuzzy.score({'address': '1st Street'}, {'address': 'First St'})
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class MatchConfidence(float, Enum):
    """Match confidence score scale."""
    PERFECT = 1.0
    VERY_HIGH = 0.95
    HIGH = 0.85
    MODERATE = 0.70
    LOW = 0.50
    VERY_LOW = 0.25
    NO_MATCH = 0.0


@dataclass
class MatchResult:
    """Result of matching two records."""
    record1_id: str
    record2_id: str
    strategy_name: str
    confidence_score: float
    field_scores: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return (f"MatchResult(record1={self.record1_id}, record2={self.record2_id}, "
                f"strategy={self.strategy_name}, score={self.confidence_score:.3f})")


class MatchingStrategy(ABC):
    """
    Base class for all matching strategies.
    
    A matching strategy compares two records and produces a confidence score
    indicating how likely they represent the same entity.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        fields: List[str],
        field_weights: Optional[Dict[str, float]] = None,
        threshold: float = 0.5,
        case_sensitive: bool = False,
        normalize: bool = True
    ):
        """
        Initialize matching strategy.
        
        Args:
            name: Strategy identifier
            description: Human-readable description
            fields: List of record fields to compare
            field_weights: Optional weights for each field (must sum to 1.0)
            threshold: Minimum confidence to consider a match
            case_sensitive: Whether to perform case-sensitive comparisons
            normalize: Whether to normalize strings before comparison
        """
        self.name = name
        self.description = description
        self.fields = fields
        self.threshold = max(0.0, min(1.0, threshold))
        self.case_sensitive = case_sensitive
        self.normalize = normalize
        
        # Validate and set field weights
        if field_weights:
            total = sum(field_weights.values())
            if not (0.99 < total < 1.01):
                raise ValueError(f"Field weights must sum to 1.0, got {total}")
            self.field_weights = field_weights
        else:
            # Equal weights if not specified
            weight = 1.0 / len(fields) if fields else 1.0
            self.field_weights = {f: weight for f in fields}
    
    def _normalize_string(self, value: str) -> str:
        """Normalize string for comparison."""
        if not isinstance(value, str):
            return str(value)
        
        # Remove diacritics
        value = ''.join(
            c for c in unicodedata.normalize('NFD', value)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Strip whitespace and optionally lowercase
        value = value.strip()
        if not self.case_sensitive:
            value = value.lower()
        
        return value
    
    def _get_field_value(self, record: Dict[str, Any], field: str) -> str:
        """Safely get field value from record."""
        value = record.get(field, '')
        if value is None:
            return ''
        if not isinstance(value, str):
            value = str(value)
        return self._normalize_string(value) if self.normalize else value
    
    @abstractmethod
    def _compare_records(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> float:
        """
        Compare two records and return confidence score.
        
        Must be implemented by subclasses.
        
        Args:
            record1: First record
            record2: Second record
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass
    
    def score(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> float:
        """
        Score match between two records.
        
        Args:
            record1: First record
            record2: Second record
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not record1 or not record2:
            return 0.0
        
        return self._compare_records(record1, record2)
    
    def match(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> MatchResult:
        """
        Perform full match analysis between two records.
        
        Args:
            record1: First record with required 'id' field
            record2: Second record with required 'id' field
            
        Returns:
            MatchResult object with detailed scoring
        """
        record1_id = str(record1.get('id', 'unknown'))
        record2_id = str(record2.get('id', 'unknown'))
        confidence = self.score(record1, record2)
        
        # Calculate per-field scores for detailed reporting
        field_scores = {}
        for field in self.fields:
            val1 = self._get_field_value(record1, field)
            val2 = self._get_field_value(record2, field)
            if val1 and val2:
                field_scores[field] = self._score_field(val1, val2)
        
        return MatchResult(
            record1_id=record1_id,
            record2_id=record2_id,
            strategy_name=self.name,
            confidence_score=confidence,
            field_scores=field_scores,
            details={'fields_compared': len(self.fields)}
        )
    
    def _score_field(self, val1: str, val2: str) -> float:
        """Score a single field match (for reporting only)."""
        if val1 == val2:
            return 1.0
        return 0.0


class ExactMatch(MatchingStrategy):
    """
    Exact string matching strategy.
    
    Records match if specified fields are identical.
    """
    
    def __init__(
        self,
        fields: List[str],
        field_weights: Optional[Dict[str, float]] = None,
        case_sensitive: bool = False,
        normalize: bool = True
    ):
        super().__init__(
            name="ExactMatch",
            description="Exact string matching on specified fields",
            fields=fields,
            field_weights=field_weights,
            threshold=1.0,
            case_sensitive=case_sensitive,
            normalize=normalize
        )
    
    def _compare_records(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> float:
        """Compare records using exact matching."""
        if not self.fields:
            return 0.0
        
        matches = 0
        for field in self.fields:
            val1 = self._get_field_value(record1, field)
            val2 = self._get_field_value(record2, field)
            if val1 and val2 and val1 == val2:
                matches += self.field_weights.get(field, 0)
        
        return min(1.0, matches)


class FuzzyMatch(MatchingStrategy):
    """
    Fuzzy string matching using token set ratio.
    
    Uses sequence matching algorithm to find similarity between strings.
    Handles typos, word order variations, and partial matches.
    """
    
    def __init__(
        self,
        fields: List[str],
        field_weights: Optional[Dict[str, float]] = None,
        threshold: float = 0.85,
        algorithm: str = 'token_set_ratio',
        normalize: bool = True
    ):
        """
        Initialize fuzzy matching strategy.
        
        Args:
            fields: Fields to compare
            field_weights: Optional field weights
            threshold: Minimum confidence score (0-1)
            algorithm: 'ratio', 'token_set_ratio', 'token_sort_ratio'
            normalize: Whether to normalize strings
        """
        super().__init__(
            name="FuzzyMatch",
            description=f"Fuzzy string matching using {algorithm}",
            fields=fields,
            field_weights=field_weights,
            threshold=threshold,
            normalize=normalize
        )
        self.algorithm = algorithm
    
    def _jaro_winkler_similarity(self, s1: str, s2: str) -> float:
        """Calculate Jaro-Winkler similarity between strings."""
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0
        
        # Jaro similarity
        len1, len2 = len(s1), len(s2)
        match_distance = max(len1, len2) // 2 - 1
        s1_matches = [False] * len1
        s2_matches = [False] * len2
        matches = 0
        transpositions = 0
        
        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(i + match_distance + 1, len2)
            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break
        
        if matches == 0:
            return 0.0
        
        for i in range(len1):
            if not s1_matches[i]:
                continue
            k = 0
            for j in range(len2):
                if not s2_matches[j]:
                    continue
                if s1[i] != s2[j]:
                    transpositions += 1
                k += 1
                break
        
        jaro = (matches / len1 + matches / len2 + 
                (matches - transpositions / 2) / matches) / 3
        
        # Jaro-Winkler
        prefix = 0
        for i in range(min(len(s1), len(s2))):
            if s1[i] == s2[i]:
                prefix += 1
            else:
                break
        prefix = min(4, prefix)
        
        return jaro + prefix * 0.1 * (1 - jaro)
    
    def _token_set_ratio(self, s1: str, s2: str) -> float:
        """Calculate token set ratio."""
        tokens1 = set(s1.split())
        tokens2 = set(s2.split())
        
        if not tokens1 or not tokens2:
            return 1.0 if tokens1 == tokens2 else 0.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        return intersection / union if union > 0 else 0.0
    
    def _compare_records(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> float:
        """Compare records using fuzzy matching."""
        if not self.fields:
            return 0.0
        
        total_score = 0.0
        for field in self.fields:
            val1 = self._get_field_value(record1, field)
            val2 = self._get_field_value(record2, field)
            
            if not val1 or not val2:
                continue
            
            if self.algorithm == 'token_set_ratio':
                field_score = self._token_set_ratio(val1, val2)
            else:
                field_score = self._jaro_winkler_similarity(val1, val2)
            
            weight = self.field_weights.get(field, 0)
            total_score += field_score * weight
        
        return min(1.0, total_score)


class PhoneticMatch(MatchingStrategy):
    """
    Phonetic matching using Soundex algorithm.
    
    Useful for matching names and addresses with spelling variations.
    """
    
    def __init__(
        self,
        fields: List[str],
        field_weights: Optional[Dict[str, float]] = None,
        threshold: float = 0.8
    ):
        super().__init__(
            name="PhoneticMatch",
            description="Phonetic matching using Soundex",
            fields=fields,
            field_weights=field_weights,
            threshold=threshold,
            normalize=True
        )
    
    def _soundex(self, s: str) -> str:
        """Generate Soundex code for a string."""
        if not s:
            return ''
        
        # Uppercase and remove non-letters
        s = ''.join(c.upper() for c in s if c.isalpha())
        if not s:
            return ''
        
        # Soundex algorithm
        first_letter = s[0]
        codes = {
            'B': '1', 'F': '1', 'P': '1', 'V': '1',
            'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
            'D': '3', 'T': '3',
            'L': '4',
            'M': '5', 'N': '5',
            'R': '6'
        }
        
        code = first_letter
        prev_code = codes.get(first_letter, '0')
        
        for char in s[1:]:
            char_code = codes.get(char, '0')
            if char_code != '0' and char_code != prev_code:
                code += char_code
                if len(code) == 4:
                    break
            if char_code != '0':
                prev_code = char_code
        
        # Pad with zeros
        return (code + '000')[:4]
    
    def _compare_records(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> float:
        """Compare records using phonetic matching."""
        if not self.fields:
            return 0.0
        
        total_score = 0.0
        for field in self.fields:
            val1 = self._get_field_value(record1, field)
            val2 = self._get_field_value(record2, field)
            
            if not val1 or not val2:
                continue
            
            # Get first word for phonetic comparison
            first_word1 = val1.split()[0] if val1.split() else val1
            first_word2 = val2.split()[0] if val2.split() else val2
            
            code1 = self._soundex(first_word1)
            code2 = self._soundex(first_word2)
            
            field_score = 1.0 if code1 and code1 == code2 else 0.0
            weight = self.field_weights.get(field, 0)
            total_score += field_score * weight
        
        return min(1.0, total_score)


class GeographicMatch(MatchingStrategy):
    """
    Geographic proximity matching using coordinates.
    
    Matches records based on spatial distance between coordinates.
    Useful for sidewalk segments, complaint locations, etc.
    """
    
    def __init__(
        self,
        lat_field: str = 'latitude',
        lon_field: str = 'longitude',
        distance_threshold_m: float = 10.0,
        threshold: float = 0.9
    ):
        """
        Initialize geographic matching.
        
        Args:
            lat_field: Field name for latitude
            lon_field: Field name for longitude
            distance_threshold_m: Maximum distance in meters to consider a match
            threshold: Confidence threshold
        """
        super().__init__(
            name="GeographicMatch",
            description=f"Geographic proximity within {distance_threshold_m}m",
            fields=[lat_field, lon_field],
            threshold=threshold
        )
        self.lat_field = lat_field
        self.lon_field = lon_field
        self.distance_threshold_m = distance_threshold_m
    
    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """Calculate Haversine distance between two coordinates in meters."""
        try:
            from math import radians, sin, cos, sqrt, atan2
        except ImportError:
            return 0.0
        
        try:
            R = 6371000  # Earth radius in meters
            
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c
            
            return distance
        except Exception:
            return float('inf')
    
    def _compare_records(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> float:
        """Compare records using geographic proximity."""
        try:
            lat1 = float(record1.get(self.lat_field, 0))
            lon1 = float(record1.get(self.lon_field, 0))
            lat2 = float(record2.get(self.lat_field, 0))
            lon2 = float(record2.get(self.lon_field, 0))
            
            if lat1 == 0 or lon1 == 0 or lat2 == 0 or lon2 == 0:
                return 0.0
            
            distance = self._haversine_distance(lat1, lon1, lat2, lon2)
            
            if distance <= self.distance_threshold_m:
                # Higher confidence for closer matches
                return 1.0 - (distance / self.distance_threshold_m)
            return 0.0
        
        except (ValueError, TypeError):
            return 0.0


class TemporalMatch(MatchingStrategy):
    """
    Temporal overlap matching.
    
    Matches records based on overlapping date ranges or temporal proximity.
    Useful for tracking same activity/entity across time.
    """
    
    def __init__(
        self,
        start_field: str = 'start_date',
        end_field: str = 'end_date',
        max_gap_days: int = 30,
        threshold: float = 0.7
    ):
        """
        Initialize temporal matching.
        
        Args:
            start_field: Field name for start date
            end_field: Field name for end date
            max_gap_days: Maximum days gap to consider overlap
            threshold: Confidence threshold
        """
        super().__init__(
            name="TemporalMatch",
            description=f"Temporal overlap within {max_gap_days} days",
            fields=[start_field, end_field],
            threshold=threshold
        )
        self.start_field = start_field
        self.end_field = end_field
        self.max_gap_days = max_gap_days
    
    def _parse_date(self, value: Any) -> Optional[datetime]:
        """Parse date from various formats."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%m/%d/%Y']:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None
    
    def _compare_records(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> float:
        """Compare records using temporal overlap."""
        try:
            start1 = self._parse_date(record1.get(self.start_field))
            end1 = self._parse_date(record1.get(self.end_field))
            start2 = self._parse_date(record2.get(self.start_field))
            end2 = self._parse_date(record2.get(self.end_field))
            
            if not all([start1, end1, start2, end2]):
                return 0.0
            
            # Check for overlap
            overlap_start = max(start1, start2)
            overlap_end = min(end1, end2)
            
            if overlap_end >= overlap_start:
                # Complete overlap
                return 1.0
            
            # Check for gap
            gap = min(abs((start2 - end1).days), abs((start1 - end2).days))
            if gap <= self.max_gap_days:
                return 1.0 - (gap / self.max_gap_days)
            
            return 0.0
        
        except (ValueError, TypeError, AttributeError):
            return 0.0


class CompositeMatch(MatchingStrategy):
    """
    Composite matching using weighted combination of multiple strategies.
    
    Combines results from multiple matching strategies with configurable weights.
    """
    
    def __init__(
        self,
        strategies: List[Tuple[MatchingStrategy, float]],
        threshold: float = 0.7
    ):
        """
        Initialize composite matching.
        
        Args:
            strategies: List of (MatchingStrategy, weight) tuples
            threshold: Minimum confidence threshold
        """
        self.strategy_list = strategies
        
        # Validate weights sum to 1.0
        total_weight = sum(w for _, w in strategies)
        if not (0.99 < total_weight < 1.01):
            raise ValueError(f"Strategy weights must sum to 1.0, got {total_weight}")
        
        # Collect all fields from sub-strategies
        all_fields = set()
        for strategy, _ in strategies:
            all_fields.update(strategy.fields)
        
        super().__init__(
            name="CompositeMatch",
            description="Composite matching from multiple strategies",
            fields=list(all_fields),
            threshold=threshold
        )
    
    def _compare_records(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> float:
        """Compare records using weighted strategy combination."""
        if not self.strategy_list:
            return 0.0
        
        total_score = 0.0
        for strategy, weight in self.strategy_list:
            score = strategy.score(record1, record2)
            total_score += score * weight
        
        return min(1.0, total_score)


class SemanticMatch(MatchingStrategy):
    """
    Semantic matching using synonym and standardization mappings.
    
    Handles standardization of field values (e.g., '1st St' vs 'First Street')
    and domain-specific synonyms.
    """
    
    def __init__(
        self,
        fields: List[str],
        synonym_map: Optional[Dict[str, List[str]]] = None,
        threshold: float = 0.8
    ):
        """
        Initialize semantic matching.
        
        Args:
            fields: Fields to compare
            synonym_map: Mapping of canonical values to synonyms
            threshold: Confidence threshold
        """
        super().__init__(
            name="SemanticMatch",
            description="Semantic matching with synonym resolution",
            fields=fields,
            threshold=threshold
        )
        self.synonym_map = synonym_map or self._default_synonym_map()
    
    def _default_synonym_map(self) -> Dict[str, List[str]]:
        """Build default synonym map for common variations."""
        return {
            # Street name standardization
            '1st': ['first', '1', '1st'],
            '2nd': ['second', '2', '2nd'],
            '3rd': ['third', '3', '3rd'],
            'street': ['st', 'str', 'street'],
            'avenue': ['ave', 'av', 'avenue'],
            'boulevard': ['blvd', 'boulevard'],
            'road': ['rd', 'road'],
            'drive': ['dr', 'drv', 'drive'],
            'east': ['e', 'east'],
            'west': ['w', 'west'],
            'north': ['n', 'north'],
            'south': ['s', 'south'],
        }
    
    def _normalize_synonyms(self, value: str) -> str:
        """Normalize value using synonym map."""
        lower_value = value.lower()
        
        for canonical, synonyms in self.synonym_map.items():
            if lower_value in synonyms:
                return canonical
        
        return lower_value
    
    def _compare_records(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> float:
        """Compare records using semantic matching."""
        if not self.fields:
            return 0.0
        
        matches = 0
        for field in self.fields:
            val1 = self._normalize_synonyms(self._get_field_value(record1, field))
            val2 = self._normalize_synonyms(self._get_field_value(record2, field))
            
            if val1 and val2 and val1 == val2:
                matches += self.field_weights.get(field, 0)
        
        return min(1.0, matches)
