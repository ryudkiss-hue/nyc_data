"""
Entity relationship tracking and graph management.

Tracks relationships between master entities (e.g., block contains segments,
segment belongs to street, street in borough) and provides graph queries.

Example:
    >>> from socrata_toolkit.entity.relationships import RelationshipGraph
    >>> graph = RelationshipGraph()
    >>> graph.add_relationship('block_123', 'segment_456', 'CONTAINS')
    >>> segments = graph.get_related_entities('block_123', 'CONTAINS')
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from collections import defaultdict


class RelationshipType(str, Enum):
    """Types of relationships between entities."""
    CONTAINS = "contains"  # A contains B
    BELONGS_TO = "belongs_to"  # A belongs to B
    ADJACENT_TO = "adjacent_to"  # A is adjacent to B
    PART_OF = "part_of"  # A is part of B
    COMPOSED_OF = "composed_of"  # A is composed of B
    INTERSECTS = "intersects"  # A intersects B
    REFERENCES = "references"  # A references B
    DERIVED_FROM = "derived_from"  # A is derived from B


@dataclass
class EntityRelationship:
    """
    Relationship between two entities.
    """
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    confidence: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    notes: str = ""
    
    def __repr__(self) -> str:
        return (f"EntityRelationship({self.source_entity_id} "
                f"{self.relationship_type.value} {self.target_entity_id})")


class RelationshipGraph:
    """
    Graph of entity relationships.
    
    Provides efficient storage and querying of entity relationships,
    supporting multiple relationship types and traversal patterns.
    """
    
    def __init__(self):
        """Initialize relationship graph."""
        # Store relationships
        self._relationships: Dict[str, EntityRelationship] = {}
        
        # Index relationships for fast lookups
        self._outgoing: Dict[str, List[str]] = defaultdict(list)  # source -> rel_ids
        self._incoming: Dict[str, List[str]] = defaultdict(list)  # target -> rel_ids
        self._by_type: Dict[str, List[str]] = defaultdict(list)  # type -> rel_ids
    
    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType | str,
        confidence: float = 1.0,
        attributes: Optional[Dict[str, Any]] = None,
        notes: str = ""
    ) -> str:
        """
        Add relationship between entities.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            rel_type: Type of relationship
            confidence: Confidence in relationship
            attributes: Optional relationship attributes
            notes: Optional notes
            
        Returns:
            Relationship ID
        """
        if isinstance(rel_type, str):
            rel_type = RelationshipType(rel_type.lower())
        
        rel_id = str(uuid.uuid4())
        
        relationship = EntityRelationship(
            relationship_id=rel_id,
            source_entity_id=source_id,
            target_entity_id=target_id,
            relationship_type=rel_type,
            confidence=max(0.0, min(1.0, confidence)),
            attributes=attributes or {},
            notes=notes
        )
        
        # Store
        self._relationships[rel_id] = relationship
        
        # Index
        self._outgoing[source_id].append(rel_id)
        self._incoming[target_id].append(rel_id)
        self._by_type[rel_type.value].append(rel_id)
        
        return rel_id
    
    def add_bidirectional_relationship(
        self,
        entity1_id: str,
        entity2_id: str,
        rel_type: RelationshipType | str,
        confidence: float = 1.0,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Add bidirectional relationship.
        
        Args:
            entity1_id: First entity
            entity2_id: Second entity
            rel_type: Relationship type (automatically reversed for opposite direction)
            confidence: Confidence
            attributes: Optional attributes
            
        Returns:
            Tuple of (forward_rel_id, backward_rel_id)
        """
        forward_id = self.add_relationship(
            entity1_id,
            entity2_id,
            rel_type,
            confidence,
            attributes
        )
        
        # Reverse relationship type
        reverse_type = self._get_reverse_type(rel_type)
        
        backward_id = self.add_relationship(
            entity2_id,
            entity1_id,
            reverse_type,
            confidence,
            attributes
        )
        
        return forward_id, backward_id
    
    def _get_reverse_type(self, rel_type: RelationshipType | str) -> RelationshipType:
        """Get reverse of relationship type."""
        if isinstance(rel_type, str):
            rel_type = RelationshipType(rel_type.lower())
        
        reverse_map = {
            RelationshipType.CONTAINS: RelationshipType.PART_OF,
            RelationshipType.PART_OF: RelationshipType.CONTAINS,
            RelationshipType.BELONGS_TO: RelationshipType.COMPOSED_OF,
            RelationshipType.COMPOSED_OF: RelationshipType.BELONGS_TO,
            RelationshipType.ADJACENT_TO: RelationshipType.ADJACENT_TO,
            RelationshipType.INTERSECTS: RelationshipType.INTERSECTS,
            RelationshipType.REFERENCES: RelationshipType.REFERENCES,
            RelationshipType.DERIVED_FROM: RelationshipType.REFERENCES,
        }
        
        return reverse_map.get(rel_type, rel_type)
    
    def get_relationship(self, rel_id: str) -> Optional[EntityRelationship]:
        """Get relationship by ID."""
        return self._relationships.get(rel_id)
    
    def remove_relationship(self, rel_id: str) -> bool:
        """Remove relationship."""
        rel = self._relationships.get(rel_id)
        if not rel:
            return False
        
        # Remove from indexes
        self._outgoing[rel.source_entity_id].remove(rel_id)
        self._incoming[rel.target_entity_id].remove(rel_id)
        self._by_type[rel.relationship_type.value].remove(rel_id)
        
        # Remove relationship
        del self._relationships[rel_id]
        
        return True
    
    def get_related_entities(
        self,
        entity_id: str,
        relationship_type: Optional[RelationshipType | str] = None,
        direction: str = "outgoing"
    ) -> List[Tuple[str, RelationshipType, float]]:
        """
        Get entities related to given entity.
        
        Args:
            entity_id: Entity ID
            relationship_type: Filter by type (None = all)
            direction: 'outgoing' or 'incoming'
            
        Returns:
            List of (related_entity_id, rel_type, confidence) tuples
        """
        if direction == "outgoing":
            rel_ids = self._outgoing.get(entity_id, [])
        else:
            rel_ids = self._incoming.get(entity_id, [])
        
        results = []
        
        for rel_id in rel_ids:
            rel = self._relationships[rel_id]
            
            # Filter by type if specified
            if relationship_type:
                if isinstance(relationship_type, str):
                    relationship_type = RelationshipType(relationship_type.lower())
                
                if rel.relationship_type != relationship_type:
                    continue
            
            # Add result
            target = rel.target_entity_id if direction == "outgoing" else rel.source_entity_id
            results.append((target, rel.relationship_type, rel.confidence))
        
        return results
    
    def get_all_relationships(
        self,
        source_id: Optional[str] = None,
        rel_type: Optional[RelationshipType | str] = None
    ) -> List[EntityRelationship]:
        """
        Get relationships matching criteria.
        
        Args:
            source_id: Filter by source (None = all)
            rel_type: Filter by type (None = all)
            
        Returns:
            List of matching relationships
        """
        results = []
        
        for rel in self._relationships.values():
            if source_id and rel.source_entity_id != source_id:
                continue
            
            if rel_type:
                if isinstance(rel_type, str):
                    rel_type = RelationshipType(rel_type.lower())
                
                if rel.relationship_type != rel_type:
                    continue
            
            results.append(rel)
        
        return results
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> Optional[List[str]]:
        """
        Find path between entities using BFS.
        
        Args:
            source_id: Start entity
            target_id: End entity
            max_depth: Maximum depth to search
            
        Returns:
            List of entity IDs forming path, or None if not found
        """
        from collections import deque
        
        if source_id == target_id:
            return [source_id]
        
        queue = deque([(source_id, [source_id])])
        visited = {source_id}
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            # Get all outgoing relationships
            related = self.get_related_entities(current, direction="outgoing")
            
            for entity_id, _, _ in related:
                if entity_id == target_id:
                    return path + [entity_id]
                
                if entity_id not in visited:
                    visited.add(entity_id)
                    queue.append((entity_id, path + [entity_id]))
        
        return None
    
    def find_all_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3
    ) -> List[List[str]]:
        """
        Find all paths between entities.
        
        Args:
            source_id: Start entity
            target_id: End entity
            max_depth: Maximum depth
            
        Returns:
            List of paths (each path is a list of entity IDs)
        """
        paths = []
        
        def dfs(current: str, target: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            
            if current == target:
                paths.append(path)
                return
            
            related = self.get_related_entities(current, direction="outgoing")
            
            for entity_id, _, _ in related:
                if entity_id not in path:  # Avoid cycles
                    dfs(entity_id, target, path + [entity_id], depth + 1)
        
        dfs(source_id, target_id, [source_id], 1)
        return paths
    
    def get_transitive_closure(
        self,
        entity_id: str,
        relationship_type: Optional[RelationshipType | str] = None
    ) -> Set[str]:
        """
        Get all entities reachable from given entity.
        
        Args:
            entity_id: Starting entity
            relationship_type: Filter by relationship type
            
        Returns:
            Set of reachable entity IDs
        """
        visited = set()
        to_visit = [entity_id]
        
        while to_visit:
            current = to_visit.pop(0)
            
            if current in visited:
                continue
            
            visited.add(current)
            
            related = self.get_related_entities(
                current,
                relationship_type=relationship_type,
                direction="outgoing"
            )
            
            for entity_id, _, _ in related:
                if entity_id not in visited:
                    to_visit.append(entity_id)
        
        visited.discard(entity_id)  # Don't include source
        return visited
    
    def export_graph(self) -> Dict[str, Any]:
        """
        Export graph as data structure.
        
        Returns:
            Dictionary with relationships
        """
        nodes = set()
        edges = []
        
        for rel in self._relationships.values():
            nodes.add(rel.source_entity_id)
            nodes.add(rel.target_entity_id)
            
            edges.append({
                'source': rel.source_entity_id,
                'target': rel.target_entity_id,
                'type': rel.relationship_type.value,
                'confidence': rel.confidence,
                'attributes': rel.attributes
            })
        
        return {
            'nodes': list(nodes),
            'edges': edges,
            'node_count': len(nodes),
            'edge_count': len(edges)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        if not self._relationships:
            return {
                'total_relationships': 0,
                'total_entities': 0,
                'relationship_types': [],
                'avg_confidence': 0.0
            }
        
        # Count unique entities
        entities = set()
        for rel in self._relationships.values():
            entities.add(rel.source_entity_id)
            entities.add(rel.target_entity_id)
        
        # Count by type
        by_type = defaultdict(int)
        for rel in self._relationships.values():
            by_type[rel.relationship_type.value] += 1
        
        # Average confidence
        avg_conf = sum(
            r.confidence for r in self._relationships.values()
        ) / len(self._relationships)
        
        return {
            'total_relationships': len(self._relationships),
            'total_entities': len(entities),
            'relationship_types': list(by_type.keys()),
            'relationships_by_type': dict(by_type),
            'avg_confidence': avg_conf,
            'max_outgoing_degree': max(
                (len(ids) for ids in self._outgoing.values()),
                default=0
            ),
            'max_incoming_degree': max(
                (len(ids) for ids in self._incoming.values()),
                default=0
            )
        }
