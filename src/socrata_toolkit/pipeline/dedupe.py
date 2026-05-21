"""
Deduplication engine for identifying and managing duplicate records.

Provides rule-based deduplication with configurable matching strategies,
blocking algorithms for scalability, and support for both hard and soft
deduplication materialization.

Example:
    >>> from socrata_toolkit.pipeline.dedupe import Deduplicator, DeduplicationRule
    >>> from socrata_toolkit.entity.matching import ExactMatch
    >>> rule = DeduplicationRule(
    ...     rule_id='sidewalk_block_match',
    ...     entity_type='sidewalk_segment',
    ...     matching_strategy=ExactMatch(fields=['block_id']),
    ...     threshold=1.0,
    ...     blocking_keys=['borough', 'block_id']
    ... )
    >>> dedup = Deduplicator()
    >>> duplicates = dedup.find_duplicates(dataset, rule)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ..entity.matching import MatchingStrategy


class MaterializationMode(str, Enum):
    """How deduplication decisions are applied."""
    HARD = "hard"  # Physically merge records
    SOFT = "soft"  # Flag duplicates, preserve originals
    REVIEW = "review"  # Queue for manual review


class DuplicateStatus(str, Enum):
    """Status of a duplicate group."""
    UNRESOLVED = "unresolved"
    AUTO_RESOLVED = "auto_resolved"
    MANUAL_RESOLVED = "manual_resolved"
    REJECTED = "rejected"  # Not actually duplicates


@dataclass
class DuplicateGroup:
    """
    Represents a group of records identified as potential duplicates.
    """
    group_id: str
    duplicate_record_ids: List[str]
    confidence_score: float
    matching_strategy: str
    matching_details: Dict[str, Any] = field(default_factory=dict)
    potential_canonical_id: Optional[str] = None
    status: DuplicateStatus = DuplicateStatus.UNRESOLVED
    user_decision: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""
    
    def __repr__(self) -> str:
        return (f"DuplicateGroup(id={self.group_id}, records={len(self.duplicate_record_ids)}, "
                f"confidence={self.confidence_score:.3f}, status={self.status.value})")


class DeduplicationRule:
    """
    Configuration for a deduplication rule.
    
    Rules define which records to compare (blocking keys), how to compare them
    (matching strategy), and when to consider them duplicates (threshold).
    """
    
    def __init__(
        self,
        rule_id: str,
        entity_type: str,
        matching_strategy: MatchingStrategy,
        threshold: float = 0.85,
        blocking_keys: Optional[List[str]] = None,
        materialization: MaterializationMode = MaterializationMode.SOFT,
        enabled: bool = True,
        max_group_size: int = 100,
        description: str = ""
    ):
        """
        Initialize deduplication rule.
        
        Args:
            rule_id: Unique rule identifier
            entity_type: Type of entity to deduplicate
            matching_strategy: Strategy for matching records
            threshold: Minimum confidence to consider duplicates
            blocking_keys: Fields to use for initial filtering
            materialization: How to apply deduplication
            enabled: Whether rule is active
            max_group_size: Maximum records in a duplicate group
            description: Human-readable description
        """
        self.rule_id = rule_id
        self.entity_type = entity_type
        self.matching_strategy = matching_strategy
        self.threshold = max(0.0, min(1.0, threshold))
        self.blocking_keys = blocking_keys or []
        self.materialization = materialization
        self.enabled = enabled
        self.max_group_size = max_group_size
        self.description = description
        self.created_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return (f"DeduplicationRule(rule_id={self.rule_id}, entity_type={self.entity_type}, "
                f"threshold={self.threshold}, strategy={self.matching_strategy.name})")


class DeduplicationResult:
    """Result of applying a deduplication rule."""
    
    def __init__(
        self,
        rule_id: str,
        duplicate_groups: List[DuplicateGroup],
        total_records: int,
        duplicates_found: int,
        execution_time_seconds: float
    ):
        self.rule_id = rule_id
        self.duplicate_groups = duplicate_groups
        self.total_records = total_records
        self.duplicates_found = duplicates_found
        self.execution_time_seconds = execution_time_seconds
        self.timestamp = datetime.now(timezone.utc)
    
    @property
    def duplicate_rate(self) -> float:
        """Percentage of records involved in duplicate groups."""
        if self.total_records == 0:
            return 0.0
        return (self.duplicates_found / self.total_records) * 100


class Deduplicator:
    """
    Deduplication engine with blocking and matching.
    
    Efficiently identifies duplicate records using:
    - Blocking keys for candidate pair reduction
    - Configurable matching strategies
    - Scalable algorithms for large datasets
    """
    
    def __init__(self):
        """Initialize deduplicator."""
        self._duplicate_registry: Dict[str, DuplicateGroup] = {}
        self._record_to_group: Dict[str, str] = {}  # record_id -> group_id
        self._canonical_mapping: Dict[str, str] = {}  # record_id -> canonical_id
    
    def _create_blocking_key(self, record: Dict[str, Any], blocking_keys: List[str]) -> str:
        """
        Create blocking key from record.
        
        Args:
            record: Input record
            blocking_keys: List of fields to use for blocking
            
        Returns:
            Blocking key string
        """
        if not blocking_keys:
            return "__all__"
        
        key_parts = []
        for field in blocking_keys:
            value = record.get(field, '')
            if value:
                # Normalize value
                value_str = str(value).strip().lower()
                key_parts.append(value_str)
        
        return "|".join(key_parts) if key_parts else "__none__"
    
    def _get_candidate_pairs(
        self,
        records: List[Dict[str, Any]],
        blocking_keys: List[str]
    ) -> List[Tuple[int, int]]:
        """
        Get candidate record pairs using blocking.
        
        Reduces comparison from O(n²) to O(n) by grouping records
        with matching blocking keys.
        
        Args:
            records: List of records
            blocking_keys: Fields for blocking
            
        Returns:
            List of (index1, index2) pairs to compare
        """
        # Group records by blocking key
        blocks: Dict[str, List[int]] = {}
        
        for idx, record in enumerate(records):
            block_key = self._create_blocking_key(record, blocking_keys)
            if block_key not in blocks:
                blocks[block_key] = []
            blocks[block_key].append(idx)
        
        # Create candidate pairs within each block
        pairs = []
        for indices in blocks.values():
            # Compare all pairs within block
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    pairs.append((indices[i], indices[j]))
        
        return pairs
    
    def find_duplicates(
        self,
        records: List[Dict[str, Any]],
        rule: DeduplicationRule
    ) -> List[DuplicateGroup]:
        """
        Find duplicates in dataset using rule.
        
        Args:
            records: List of records to deduplicate
            rule: Deduplication rule to apply
            
        Returns:
            List of DuplicateGroup objects
        """
        if not rule.enabled or not records:
            return []
        
        # Get candidate pairs
        pairs = self._get_candidate_pairs(records, rule.blocking_keys)
        
        if not pairs:
            return []
        
        # Score each pair
        scored_pairs: List[Tuple[int, int, float]] = []
        for idx1, idx2 in pairs:
            score = rule.matching_strategy.score(records[idx1], records[idx2])
            if score >= rule.threshold:
                scored_pairs.append((idx1, idx2, score))
        
        if not scored_pairs:
            return []
        
        # Cluster records into duplicate groups
        duplicate_groups = self._cluster_duplicates(records, scored_pairs, rule)
        
        return duplicate_groups
    
    def _cluster_duplicates(
        self,
        records: List[Dict[str, Any]],
        scored_pairs: List[Tuple[int, int, float]],
        rule: DeduplicationRule
    ) -> List[DuplicateGroup]:
        """
        Cluster record pairs into duplicate groups.
        
        Uses union-find algorithm to efficiently group related records.
        """
        # Union-find data structure
        parent: Dict[int, int] = {}
        
        def find(x: int) -> int:
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x: int, y: int) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        # Build groups from scored pairs
        pair_scores: Dict[Tuple[int, int], float] = {}
        for idx1, idx2, score in scored_pairs:
            union(idx1, idx2)
            pair_scores[(min(idx1, idx2), max(idx1, idx2))] = score
        
        # Collect groups
        groups_dict: Dict[int, List[int]] = {}
        for idx in range(len(records)):
            if scored_pairs:  # Only if we found some pairs
                root = find(idx)
                if root not in groups_dict:
                    groups_dict[root] = []
                groups_dict[root].append(idx)
        
        # Filter groups (must have 2+ records)
        duplicate_groups = []
        for root, indices in groups_dict.items():
            if len(indices) >= 2 and len(indices) <= rule.max_group_size:
                record_ids = [str(records[i].get('id', i)) for i in indices]
                
                # Calculate group confidence (average of pair scores)
                group_scores = []
                for i in range(len(indices)):
                    for j in range(i + 1, len(indices)):
                        key = (min(indices[i], indices[j]), max(indices[i], indices[j]))
                        if key in pair_scores:
                            group_scores.append(pair_scores[key])
                
                avg_confidence = sum(group_scores) / len(group_scores) if group_scores else 0.0
                
                # Suggest canonical (usually first or most complete record)
                canonical_idx = max(indices, key=lambda i: len(str(records[i].get('id', ''))))
                canonical_id = str(records[canonical_idx].get('id', canonical_idx))
                
                group = DuplicateGroup(
                    group_id=str(uuid.uuid4()),
                    duplicate_record_ids=record_ids,
                    confidence_score=avg_confidence,
                    matching_strategy=rule.matching_strategy.name,
                    matching_details={
                        'rule_id': rule.rule_id,
                        'pair_count': len([s for s in group_scores if s >= rule.threshold])
                    },
                    potential_canonical_id=canonical_id
                )
                
                duplicate_groups.append(group)
                
                # Register group
                self._duplicate_registry[group.group_id] = group
                for record_id in record_ids:
                    self._record_to_group[record_id] = group.group_id
        
        return duplicate_groups
    
    def apply_rule(
        self,
        records: List[Dict[str, Any]],
        rule: DeduplicationRule
    ) -> DeduplicationResult:
        """
        Apply deduplication rule to dataset.
        
        Args:
            records: List of records
            rule: Deduplication rule
            
        Returns:
            DeduplicationResult with findings
        """
        import time
        start_time = time.time()
        
        duplicate_groups = self.find_duplicates(records, rule)
        
        duplicates_found = sum(len(g.duplicate_record_ids) for g in duplicate_groups)
        execution_time = time.time() - start_time
        
        return DeduplicationResult(
            rule_id=rule.rule_id,
            duplicate_groups=duplicate_groups,
            total_records=len(records),
            duplicates_found=duplicates_found,
            execution_time_seconds=execution_time
        )
    
    def mark_as_duplicates(
        self,
        record_ids: List[str],
        canonical_id: str,
        reason: str = "",
        user: Optional[str] = None
    ) -> bool:
        """
        Manually mark records as duplicates of canonical.
        
        Args:
            record_ids: IDs of duplicate records
            canonical_id: ID of canonical record
            reason: Reason for marking as duplicates
            user: User who made the decision
            
        Returns:
            Success status
        """
        if not record_ids or canonical_id not in record_ids:
            return False
        
        # Create or update duplicate group
        group_id = str(uuid.uuid4())
        group = DuplicateGroup(
            group_id=group_id,
            duplicate_record_ids=record_ids,
            confidence_score=1.0,  # Manual
            matching_strategy="MANUAL",
            potential_canonical_id=canonical_id,
            status=DuplicateStatus.MANUAL_RESOLVED,
            user_decision=f"marked_by_{user}" if user else "marked_manually",
            notes=reason
        )
        
        self._duplicate_registry[group_id] = group
        for record_id in record_ids:
            self._record_to_group[record_id] = group_id
            self._canonical_mapping[record_id] = canonical_id
        
        return True
    
    def unmark_duplicates(self, record_ids: List[str]) -> bool:
        """
        Remove duplicate markings for records.
        
        Args:
            record_ids: IDs of records to unmark
            
        Returns:
            Success status
        """
        for record_id in record_ids:
            self._record_to_group.pop(record_id, None)
            self._canonical_mapping.pop(record_id, None)
        
        return True
    
    def get_duplicates_for_record(self, record_id: str) -> List[str]:
        """
        Get all records identified as duplicates for a record.
        
        Args:
            record_id: Record ID to query
            
        Returns:
            List of duplicate record IDs (excluding the input record)
        """
        group_id = self._record_to_group.get(record_id)
        if not group_id:
            return []
        
        group = self._duplicate_registry.get(group_id)
        if not group:
            return []
        
        return [rid for rid in group.duplicate_record_ids if rid != record_id]
    
    def get_canonical_for_record(self, record_id: str) -> Optional[str]:
        """
        Get canonical ID for a record if it's a duplicate.
        
        Args:
            record_id: Record ID to query
            
        Returns:
            Canonical record ID or None
        """
        return self._canonical_mapping.get(record_id)
    
    def get_duplicate_group(self, group_id: str) -> Optional[DuplicateGroup]:
        """Get a duplicate group by ID."""
        return self._duplicate_registry.get(group_id)
    
    def resolve_group(
        self,
        group_id: str,
        canonical_id: str,
        user: Optional[str] = None,
        notes: str = ""
    ) -> bool:
        """
        Resolve a duplicate group by selecting canonical.
        
        Args:
            group_id: Group ID
            canonical_id: ID of canonical record
            user: User making the decision
            notes: Additional notes
            
        Returns:
            Success status
        """
        group = self._duplicate_registry.get(group_id)
        if not group:
            return False
        
        group.potential_canonical_id = canonical_id
        group.status = DuplicateStatus.MANUAL_RESOLVED
        group.user_decision = f"resolved_by_{user}" if user else "resolved_manually"
        group.notes = notes
        group.timestamp = datetime.now(timezone.utc)
        
        # Update canonical mapping
        for record_id in group.duplicate_record_ids:
            if record_id != canonical_id:
                self._canonical_mapping[record_id] = canonical_id
        
        return True
    
    def get_unresolved_groups(self) -> List[DuplicateGroup]:
        """Get all unresolved duplicate groups."""
        return [
            g for g in self._duplicate_registry.values()
            if g.status == DuplicateStatus.UNRESOLVED
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get deduplication statistics.
        
        Returns:
            Dictionary with statistics
        """
        groups = list(self._duplicate_registry.values())
        
        return {
            'total_groups': len(groups),
            'total_duplicate_records': sum(len(g.duplicate_record_ids) for g in groups),
            'unresolved_groups': len([g for g in groups if g.status == DuplicateStatus.UNRESOLVED]),
            'resolved_groups': len([g for g in groups if g.status != DuplicateStatus.UNRESOLVED]),
            'average_confidence': sum(g.confidence_score for g in groups) / len(groups) if groups else 0.0,
            'max_group_size': max((len(g.duplicate_record_ids) for g in groups), default=0),
            'duplicate_strategies': list(set(g.matching_strategy for g in groups))
        }
