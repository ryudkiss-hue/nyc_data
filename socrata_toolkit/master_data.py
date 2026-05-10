"""
Master Data Management (MDM) for entity resolution.

Manages creation and maintenance of master entities from deduplicated records,
including canonical representation, field-level confidence, and merge strategies.

Example:
    >>> from socrata_toolkit.master_data import MasterDataManager, EntityMergeStrategy
    >>> mgr = MasterDataManager()
    >>> entity_id = mgr.create_master_entity(
    ...     record1={'id': '1', 'name': 'John Doe', 'address': '123 Main St'},
    ...     record2={'id': '2', 'name': 'John Doe', 'address': '123 Main Street'}
    ... )
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .deduplication import DuplicateGroup


class EntityMergeStrategy(str, Enum):
    """Strategy for resolving field conflicts during merge."""
    PICK_FIRST = "pick_first"
    PICK_LATEST = "pick_latest"
    PICK_MOST_COMMON = "pick_most_common"
    WEIGHTED_AVERAGE = "weighted_average"
    CUSTOM = "custom"


@dataclass
class MasterEntity:
    """Canonical representation of a unique entity."""
    entity_id: str
    entity_type: str
    canonical_record: Dict[str, Any] = field(default_factory=dict)
    source_record_ids: List[str] = field(default_factory=list)
    confidence_by_field: Dict[str, float] = field(default_factory=dict)
    field_provenance: Dict[str, str] = field(default_factory=dict)  # field -> record_id
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    merge_history: List[Dict[str, Any]] = field(default_factory=list)
    external_links: Dict[str, str] = field(default_factory=dict)  # source -> external_id
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return (f"MasterEntity(entity_id={self.entity_id}, type={self.entity_type}, "
                f"sources={len(self.source_record_ids)}, version={self.version})")


class MasterDataManager:
    """
    Manager for master data entities.
    
    Handles creation, merging, updating, and reconciliation of master entities.
    Supports multiple merge strategies and tracks field-level provenance.
    """
    
    def __init__(self, custom_merge_func: Optional[Callable] = None):
        """
        Initialize manager.
        
        Args:
            custom_merge_func: Optional custom merge strategy function
        """
        self._entities: Dict[str, MasterEntity] = {}
        self._record_to_entity: Dict[str, str] = {}  # source record -> entity
        self._custom_merge_func = custom_merge_func
        self._merge_log: List[Dict[str, Any]] = []
    
    def create_master_entity(
        self,
        entity_type: str,
        *source_records: Dict[str, Any],
        merge_strategy: EntityMergeStrategy = EntityMergeStrategy.PICK_LATEST,
        entity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a master entity from source records.
        
        Args:
            entity_type: Type of entity
            *source_records: One or more source records to merge
            merge_strategy: How to resolve conflicts
            entity_id: Optional custom entity ID
            metadata: Optional metadata
            
        Returns:
            Entity ID of created master entity
        """
        if not source_records:
            raise ValueError("At least one source record required")
        
        entity_id = entity_id or str(uuid.uuid4())
        
        # Extract record IDs
        source_record_ids = [
            str(r.get('id', f'record_{i}'))
            for i, r in enumerate(source_records)
        ]
        
        # Merge records
        canonical, confidence_by_field, provenance = self._merge_records(
            source_records,
            merge_strategy
        )
        
        # Create master entity
        entity = MasterEntity(
            entity_id=entity_id,
            entity_type=entity_type,
            canonical_record=canonical,
            source_record_ids=source_record_ids,
            confidence_by_field=confidence_by_field,
            field_provenance=provenance,
            metadata=metadata or {}
        )
        
        # Register
        self._entities[entity_id] = entity
        for record_id in source_record_ids:
            self._record_to_entity[record_id] = entity_id
        
        return entity_id
    
    def merge_duplicates(
        self,
        duplicate_group: DuplicateGroup,
        source_records: Dict[str, Dict[str, Any]],
        merge_strategy: EntityMergeStrategy = EntityMergeStrategy.PICK_LATEST,
        entity_type: str = "unknown"
    ) -> str:
        """
        Create master entity from duplicate group.
        
        Args:
            duplicate_group: DuplicateGroup to merge
            source_records: Mapping of record_id -> record_data
            merge_strategy: Merge strategy
            entity_type: Type of entity
            
        Returns:
            Entity ID of created master
        """
        records_to_merge = [
            source_records[rid]
            for rid in duplicate_group.duplicate_record_ids
            if rid in source_records
        ]
        
        if not records_to_merge:
            raise ValueError("No valid source records found in duplicate group")
        
        # Use suggested canonical if available
        entity_id = None
        if duplicate_group.potential_canonical_id:
            entity_id = f"entity_{duplicate_group.potential_canonical_id}"
        
        metadata = {
            'duplicate_group_id': duplicate_group.group_id,
            'duplicate_confidence': duplicate_group.confidence_score,
            'matching_strategy': duplicate_group.matching_strategy
        }
        
        return self.create_master_entity(
            entity_type=entity_type,
            *records_to_merge,
            merge_strategy=merge_strategy,
            entity_id=entity_id,
            metadata=metadata
        )
    
    def _merge_records(
        self,
        records: List[Dict[str, Any]],
        strategy: EntityMergeStrategy
    ) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, str]]:
        """
        Merge multiple records into canonical form.
        
        Returns:
            Tuple of (canonical_record, confidence_by_field, field_provenance)
        """
        if not records:
            return {}, {}, {}
        
        if strategy == EntityMergeStrategy.CUSTOM and self._custom_merge_func:
            return self._custom_merge_func(records)
        
        canonical = {}
        confidence_by_field = {}
        field_provenance = {}
        
        # Collect all fields
        all_fields = set()
        for record in records:
            all_fields.update(record.keys())
        
        # Remove ID field from merging
        all_fields.discard('id')
        
        for field in all_fields:
            values = [
                (i, records[i].get(field))
                for i in range(len(records))
                if field in records[i] and records[i].get(field) is not None
            ]
            
            if not values:
                continue
            
            if strategy == EntityMergeStrategy.PICK_FIRST:
                idx, value = values[0]
                canonical[field] = value
                confidence_by_field[field] = 1.0 if len(values) == 1 else 0.8
                field_provenance[field] = str(records[idx].get('id', idx))
            
            elif strategy == EntityMergeStrategy.PICK_LATEST:
                # Use most recently updated (if available)
                idx, value = values[-1]
                canonical[field] = value
                confidence_by_field[field] = 1.0 if len(values) == 1 else 0.85
                field_provenance[field] = str(records[idx].get('id', idx))
            
            elif strategy == EntityMergeStrategy.PICK_MOST_COMMON:
                # Use most frequent value
                from collections import Counter
                value_counts = Counter(v for _, v in values)
                most_common_value = value_counts.most_common(1)[0][0]
                count = value_counts.most_common(1)[0][1]
                
                canonical[field] = most_common_value
                confidence = count / len(records)
                confidence_by_field[field] = confidence
                
                # Find first record with this value
                for idx, value in values:
                    if value == most_common_value:
                        field_provenance[field] = str(records[idx].get('id', idx))
                        break
            
            elif strategy == EntityMergeStrategy.WEIGHTED_AVERAGE:
                # For numeric fields, use weighted average
                try:
                    numeric_values = [
                        float(v) for _, v in values
                        if isinstance(v, (int, float)) or
                        (isinstance(v, str) and v.replace('.', '').isdigit())
                    ]
                    if numeric_values:
                        canonical[field] = sum(numeric_values) / len(numeric_values)
                        confidence_by_field[field] = 0.9
                        field_provenance[field] = str(records[values[0][0]].get('id', 0))
                    else:
                        # Non-numeric, use pick latest
                        idx, value = values[-1]
                        canonical[field] = value
                        confidence_by_field[field] = 0.7
                        field_provenance[field] = str(records[idx].get('id', idx))
                except (ValueError, TypeError):
                    idx, value = values[-1]
                    canonical[field] = value
                    confidence_by_field[field] = 0.7
                    field_provenance[field] = str(records[idx].get('id', idx))
        
        return canonical, confidence_by_field, field_provenance
    
    def add_record_to_entity(
        self,
        entity_id: str,
        record: Dict[str, Any],
        merge_strategy: EntityMergeStrategy = EntityMergeStrategy.PICK_LATEST
    ) -> bool:
        """
        Add a record to existing master entity (re-merge).
        
        Args:
            entity_id: Master entity ID
            record: Record to add
            merge_strategy: Merge strategy
            
        Returns:
            Success status
        """
        entity = self._entities.get(entity_id)
        if not entity:
            return False
        
        record_id = str(record.get('id', f'record_{len(entity.source_record_ids)}'))
        
        # Get all source records
        source_records = [entity.canonical_record.copy()]
        source_records.append(record)
        
        # Re-merge
        canonical, confidence, provenance = self._merge_records(
            source_records,
            merge_strategy
        )
        
        # Update entity
        entity.canonical_record = canonical
        entity.confidence_by_field = confidence
        entity.field_provenance = provenance
        entity.source_record_ids.append(record_id)
        entity.last_updated = datetime.utcnow()
        entity.version += 1
        
        # Record merge operation
        entity.merge_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'added_record',
            'record_id': record_id,
            'strategy': merge_strategy.value
        })
        
        # Register record
        self._record_to_entity[record_id] = entity_id
        
        return True
    
    def get_master_entity(self, entity_id: str) -> Optional[MasterEntity]:
        """Get a master entity by ID."""
        return self._entities.get(entity_id)
    
    def get_master_for_record(self, record_id: str) -> Optional[MasterEntity]:
        """Get master entity that contains a source record."""
        entity_id = self._record_to_entity.get(record_id)
        if not entity_id:
            return None
        return self._entities.get(entity_id)
    
    def resolve_field_conflict(
        self,
        entity_id: str,
        field: str,
        value: Any,
        user: Optional[str] = None
    ) -> bool:
        """
        Manually resolve a field conflict in a master entity.
        
        Args:
            entity_id: Master entity ID
            field: Field name
            value: Chosen value
            user: User making decision
            
        Returns:
            Success status
        """
        entity = self._entities.get(entity_id)
        if not entity:
            return False
        
        entity.canonical_record[field] = value
        entity.confidence_by_field[field] = 1.0  # User-decided
        entity.last_updated = datetime.utcnow()
        
        entity.merge_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'resolved_conflict',
            'field': field,
            'value': str(value)[:100],
            'user': user or 'system'
        })
        
        return True
    
    def validate_merge(
        self,
        entity_id: str,
        required_fields: Optional[List[str]] = None,
        min_confidence: float = 0.7
    ) -> Tuple[bool, List[str]]:
        """
        Validate that a master entity meets quality criteria.
        
        Args:
            entity_id: Master entity ID
            required_fields: Fields that must be present
            min_confidence: Minimum acceptable confidence
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        entity = self._entities.get(entity_id)
        if not entity:
            return False, ["Entity not found"]
        
        issues = []
        
        # Check required fields
        if required_fields:
            for field in required_fields:
                if field not in entity.canonical_record or not entity.canonical_record[field]:
                    issues.append(f"Missing required field: {field}")
        
        # Check confidence levels
        low_confidence_fields = [
            f for f, conf in entity.confidence_by_field.items()
            if conf < min_confidence
        ]
        if low_confidence_fields:
            issues.append(f"Low confidence fields: {', '.join(low_confidence_fields)}")
        
        return len(issues) == 0, issues
    
    def export_master_data(
        self,
        entity_type: Optional[str] = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Export master data as records.
        
        Args:
            entity_type: Filter by entity type (None = all)
            include_metadata: Include confidence and provenance
            
        Returns:
            List of exported master entities
        """
        exported = []
        
        for entity in self._entities.values():
            if entity_type and entity.entity_type != entity_type:
                continue
            
            record = {
                'entity_id': entity.entity_id,
                'entity_type': entity.entity_type,
                **entity.canonical_record
            }
            
            if include_metadata:
                record['_master_metadata'] = {
                    'source_record_ids': entity.source_record_ids,
                    'confidence_by_field': entity.confidence_by_field,
                    'version': entity.version,
                    'created_at': entity.created_at.isoformat(),
                    'last_updated': entity.last_updated.isoformat()
                }
            
            exported.append(record)
        
        return exported
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get master data management statistics."""
        entities = list(self._entities.values())
        
        if not entities:
            return {
                'total_entities': 0,
                'total_source_records': 0,
                'entity_types': []
            }
        
        # Group by type
        by_type = {}
        for entity in entities:
            if entity.entity_type not in by_type:
                by_type[entity.entity_type] = []
            by_type[entity.entity_type].append(entity)
        
        return {
            'total_entities': len(entities),
            'total_source_records': sum(len(e.source_record_ids) for e in entities),
            'entity_types': list(by_type.keys()),
            'entities_by_type': {
                etype: len(entites) for etype, entites in by_type.items()
            },
            'average_merge_ratio': sum(
                len(e.source_record_ids) for e in entities
            ) / len(entities),
            'average_confidence': sum(
                sum(e.confidence_by_field.values()) / len(e.confidence_by_field)
                for e in entities if e.confidence_by_field
            ) / len(entities) if entities else 0.0
        }
    
    def link_external_master(
        self,
        entity_id: str,
        external_source: str,
        external_id: str,
        confidence: float = 1.0
    ) -> bool:
        """
        Link master entity to external master data source.
        
        Args:
            entity_id: Local master entity ID
            external_source: Name of external source (e.g., 'NYC_CARTO')
            external_id: ID in external system
            confidence: Confidence of link
            
        Returns:
            Success status
        """
        entity = self._entities.get(entity_id)
        if not entity:
            return False
        
        entity.external_links[external_source] = external_id
        entity.metadata[f'external_confidence_{external_source}'] = confidence
        entity.last_updated = datetime.utcnow()
        
        return True
    
    def find_by_canonical_value(
        self,
        field: str,
        value: Any
    ) -> List[MasterEntity]:
        """
        Find master entities by canonical field value.
        
        Args:
            field: Field to search
            value: Value to match
            
        Returns:
            List of matching master entities
        """
        matches = []
        
        for entity in self._entities.values():
            if entity.canonical_record.get(field) == value:
                matches.append(entity)
        
        return matches
