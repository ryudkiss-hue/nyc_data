"""
Reconciliation of internal master entities with external master data sources.

Handles linking to external systems (e.g., NYC CARTO, DOT systems),
detecting unlinked records, and flagging conflicts.

Example:
    >>> from socrata_toolkit.entity_reconciliation import Reconciler
    >>> reconciler = Reconciler(master_data_manager)
    >>> reconciler.import_external_master('NYC_CARTO', external_data)
    >>> report = reconciler.reconcile_to_external('NYC_CARTO')
    >>> print(f"Matched: {report.matched_count}, Unlinked: {report.unlinked_count}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .entity_matching import MatchingStrategy, FuzzyMatch
from .master_data import MasterDataManager, MasterEntity


class LinkStatus(str, Enum):
    """Status of link between internal and external entity."""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    CONFLICTING = "conflicting"
    PENDING_VERIFICATION = "pending_verification"
    BROKEN = "broken"


@dataclass
class ExternalMasterLink:
    """Link between internal and external master entity."""
    link_id: str
    local_entity_id: str
    external_source: str
    external_entity_id: str
    confidence: float
    status: LinkStatus = LinkStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_verified: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    notes: str = ""


@dataclass
class ReconciliationConflict:
    """Conflict identified during reconciliation."""
    conflict_id: str
    local_entity_id: str
    external_source: str
    external_entity_id: str
    conflict_type: str  # 'field_mismatch', 'multiple_matches', 'no_match'
    field_conflicts: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)  # field -> (local, external)
    severity: str = "medium"  # low, medium, high, critical
    resolution: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReconciliationReport:
    """Report on reconciliation with external master."""
    external_source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Counts
    total_internal_entities: int = 0
    total_external_entities: int = 0
    matched_count: int = 0
    unlinked_local: int = 0
    unlinked_external: int = 0
    
    # Quality metrics
    match_confidence: List[float] = field(default_factory=list)
    conflicts: List[ReconciliationConflict] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def match_rate(self) -> float:
        """Percentage of internal entities linked."""
        if self.total_internal_entities == 0:
            return 0.0
        return (self.matched_count / self.total_internal_entities) * 100
    
    @property
    def avg_confidence(self) -> float:
        """Average matching confidence."""
        if not self.match_confidence:
            return 0.0
        return sum(self.match_confidence) / len(self.match_confidence)


class Reconciler:
    """
    Reconciles internal master data with external sources.
    
    Handles matching, linking, conflict detection, and provides
    recommendations for resolving discrepancies.
    """
    
    def __init__(
        self,
        master_data_manager: MasterDataManager,
        matching_strategy: Optional[MatchingStrategy] = None
    ):
        """
        Initialize reconciler.
        
        Args:
            master_data_manager: Manager with internal master entities
            matching_strategy: Strategy for matching (default: FuzzyMatch)
        """
        self.master_data = master_data_manager
        self.matching_strategy = matching_strategy or FuzzyMatch(
            fields=['name', 'address'],
            threshold=0.8
        )
        
        # External master data
        self._external_masters: Dict[str, List[Dict[str, Any]]] = {}
        
        # Links and conflicts
        self._links: Dict[str, ExternalMasterLink] = {}
        self._conflicts: Dict[str, ReconciliationConflict] = {}
        
        # Reconciliation history
        self._reconciliation_reports: List[ReconciliationReport] = []
    
    def import_external_master(
        self,
        source_name: str,
        external_data: List[Dict[str, Any]]
    ) -> int:
        """
        Import external master data.
        
        Args:
            source_name: Name of external source
            external_data: List of external entities
            
        Returns:
            Number of entities imported
        """
        self._external_masters[source_name] = external_data
        return len(external_data)
    
    def reconcile_to_external(
        self,
        external_source: str,
        entity_type: Optional[str] = None,
        match_threshold: float = 0.85
    ) -> ReconciliationReport:
        """
        Reconcile internal masters to external source.
        
        Args:
            external_source: Name of external source
            entity_type: Filter by entity type
            match_threshold: Minimum confidence to link
            
        Returns:
            ReconciliationReport
        """
        if external_source not in self._external_masters:
            raise ValueError(f"External master '{external_source}' not imported")
        
        external_data = self._external_masters[external_source]
        
        # Get internal entities to reconcile
        internal_entities = [
            e for e in self.master_data._entities.values()
            if not entity_type or e.entity_type == entity_type
        ]
        
        # Try to match each internal entity to external
        matched_count = 0
        match_confidences = []
        external_matched_ids = set()
        
        for internal in internal_entities:
            best_match = None
            best_score = 0.0
            candidates = []
            
            for ext_idx, external in enumerate(external_data):
                score = self.matching_strategy.score(
                    internal.canonical_record,
                    external
                )
                
                if score > best_score:
                    best_score = score
                    best_match = (ext_idx, external, score)
                
                if score >= match_threshold:
                    candidates.append((ext_idx, external, score))
            
            # Create link if match found
            if best_match and best_score >= match_threshold:
                ext_idx, external, score = best_match
                ext_id = str(external.get('id', f'external_{ext_idx}'))
                
                self._create_link(
                    internal.entity_id,
                    external_source,
                    ext_id,
                    score
                )
                
                matched_count += 1
                match_confidences.append(score)
                external_matched_ids.add(ext_id)
                
                # Check for field-level conflicts
                self._check_field_conflicts(
                    internal,
                    external,
                    external_source,
                    score
                )
        
        # Detect unlinked
        unlinked_local = len(internal_entities) - matched_count
        unlinked_external = len(external_data) - len(external_matched_ids)
        
        # Build report
        report = ReconciliationReport(
            external_source=external_source,
            total_internal_entities=len(internal_entities),
            total_external_entities=len(external_data),
            matched_count=matched_count,
            unlinked_local=unlinked_local,
            unlinked_external=unlinked_external,
            match_confidence=match_confidences,
            conflicts=list(self._conflicts.values())
        )
        
        # Add recommendations
        if unlinked_external > 0:
            report.recommendations.append(
                f"{unlinked_external} external entities have no local match - "
                f"review for new entities"
            )
        
        if unlinked_local > 0:
            report.recommendations.append(
                f"{unlinked_local} local entities not linked to external source - "
                f"review for coverage gaps"
            )
        
        high_conflict = sum(
            1 for c in report.conflicts
            if c.severity in ['high', 'critical']
        )
        if high_conflict > 0:
            report.recommendations.append(
                f"{high_conflict} high-severity conflicts detected - manual review needed"
            )
        
        # Store report
        self._reconciliation_reports.append(report)
        
        return report
    
    def _create_link(
        self,
        local_entity_id: str,
        external_source: str,
        external_entity_id: str,
        confidence: float
    ) -> str:
        """Create link between entities."""
        import uuid
        
        link_id = str(uuid.uuid4())
        
        link = ExternalMasterLink(
            link_id=link_id,
            local_entity_id=local_entity_id,
            external_source=external_source,
            external_entity_id=external_entity_id,
            confidence=confidence
        )
        
        self._links[link_id] = link
        
        # Also store in master entity
        entity = self.master_data.get_master_entity(local_entity_id)
        if entity:
            entity.link_external_master(
                local_entity_id,
                external_source,
                external_entity_id,
                confidence
            )
        
        return link_id
    
    def _check_field_conflicts(
        self,
        internal: MasterEntity,
        external: Dict[str, Any],
        external_source: str,
        match_confidence: float
    ) -> None:
        """Check for field-level conflicts between entities."""
        import uuid
        
        conflicts_found = {}
        
        # Compare common fields
        for field in internal.canonical_record.keys():
            if field not in external:
                continue
            
            internal_val = internal.canonical_record.get(field)
            external_val = external.get(field)
            
            # Skip None values
            if not internal_val or not external_val:
                continue
            
            # Check for mismatch
            if str(internal_val).lower() != str(external_val).lower():
                conflicts_found[field] = (internal_val, external_val)
        
        # Create conflict record if issues found
        if conflicts_found:
            conflict_id = str(uuid.uuid4())
            
            conflict = ReconciliationConflict(
                conflict_id=conflict_id,
                local_entity_id=internal.entity_id,
                external_source=external_source,
                external_entity_id=str(external.get('id', 'unknown')),
                conflict_type='field_mismatch',
                field_conflicts=conflicts_found,
                severity='medium' if len(conflicts_found) <= 2 else 'high'
            )
            
            self._conflicts[conflict_id] = conflict
    
    def get_links_for_entity(self, entity_id: str) -> List[ExternalMasterLink]:
        """Get all external links for an entity."""
        return [
            link for link in self._links.values()
            if link.local_entity_id == entity_id
        ]
    
    def get_link_for_source(
        self,
        entity_id: str,
        external_source: str
    ) -> Optional[ExternalMasterLink]:
        """Get link to specific external source."""
        for link in self._links.values():
            if (link.local_entity_id == entity_id and
                link.external_source == external_source):
                return link
        return None
    
    def detect_unlinked_locals(self, external_source: str) -> List[str]:
        """Get local entities not linked to external source."""
        linked_ids = set(
            link.local_entity_id
            for link in self._links.values()
            if link.external_source == external_source
        )
        
        all_ids = set(self.master_data._entities.keys())
        return list(all_ids - linked_ids)
    
    def detect_unlinked_external(self, external_source: str) -> List[str]:
        """Get external entities not linked to local masters."""
        if external_source not in self._external_masters:
            return []
        
        linked_external = set(
            link.external_entity_id
            for link in self._links.values()
            if link.external_source == external_source
        )
        
        all_external = set(
            str(e.get('id', i))
            for i, e in enumerate(self._external_masters[external_source])
        )
        
        return list(all_external - linked_external)
    
    def merge_external_into_local(
        self,
        local_entity_id: str,
        external_source: str,
        external_entity_id: str,
        strategy: str = "prefer_local"
    ) -> bool:
        """
        Merge external entity into local master.
        
        Args:
            local_entity_id: Local master entity ID
            external_source: External source name
            external_entity_id: External entity ID
            strategy: 'prefer_local', 'prefer_external', 'merge'
            
        Returns:
            Success status
        """
        # Get entities
        local = self.master_data.get_master_entity(local_entity_id)
        if not local:
            return False
        
        if external_source not in self._external_masters:
            return False
        
        # Find external
        external = None
        for ext in self._external_masters[external_source]:
            if str(ext.get('id')) == str(external_entity_id):
                external = ext
                break
        
        if not external:
            return False
        
        # Merge based on strategy
        if strategy == "prefer_external":
            for field, value in external.items():
                if field != 'id' and value is not None:
                    local.canonical_record[field] = value
                    local.confidence_by_field[field] = 0.95
                    local.field_provenance[field] = external_source
        
        elif strategy == "merge":
            # Keep local values, fill gaps from external
            for field, value in external.items():
                if field != 'id' and (
                    field not in local.canonical_record or
                    not local.canonical_record[field]
                ):
                    local.canonical_record[field] = value
                    local.confidence_by_field[field] = 0.85
                    local.field_provenance[field] = f"{external_source}_fill"
        
        # Create/update link
        link = self.get_link_for_source(local_entity_id, external_source)
        if not link:
            self._create_link(local_entity_id, external_source, external_entity_id, 0.95)
        else:
            link.confidence = 0.95
            link.last_verified = datetime.utcnow()
        
        return True
    
    def flag_conflict(
        self,
        conflict_id: str,
        resolution: str
    ) -> bool:
        """
        Flag and set resolution for conflict.
        
        Args:
            conflict_id: Conflict ID
            resolution: Resolution description
            
        Returns:
            Success status
        """
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            return False
        
        conflict.resolution = resolution
        return True
    
    def get_reconciliation_history(
        self,
        external_source: Optional[str] = None
    ) -> List[ReconciliationReport]:
        """Get reconciliation reports."""
        if external_source:
            return [
                r for r in self._reconciliation_reports
                if r.external_source == external_source
            ]
        return self._reconciliation_reports.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get reconciliation statistics."""
        return {
            'external_sources_imported': len(self._external_masters),
            'total_links': len(self._links),
            'active_links': sum(
                1 for l in self._links.values()
                if l.status == LinkStatus.ACTIVE
            ),
            'conflicts': len(self._conflicts),
            'reconciliation_reports': len(self._reconciliation_reports),
            'avg_link_confidence': (
                sum(l.confidence for l in self._links.values()) / len(self._links)
                if self._links else 0.0
            )
        }
