"""
Incremental entity matching for new records.

Efficiently matches new records against existing master data,
supporting both auto-assignment and manual review workflows.

Example:
    >>> from socrata_toolkit.entity_incremental import IncrementalMatcher
    >>> matcher = IncrementalMatcher(master_data_manager)
    >>> result = matcher.match_against_existing(new_record)
    >>> if result.confidence >= 0.95:
    ...     matcher.assign_to_entity(new_record['id'], result.entity_id)
    ... else:
    ...     matcher.queue_for_review(new_record['id'], result.matches)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .entity_matching import MatchingStrategy, CompositeMatch, FuzzyMatch, ExactMatch
from .master_data import MasterDataManager, MasterEntity


class MatchDecision(str, Enum):
    """Decision on new record matching."""
    AUTO_ASSIGNED = "auto_assigned"
    QUEUED_FOR_REVIEW = "queued_for_review"
    UNMATCHED = "unmatched"
    MANUAL_OVERRIDE = "manual_override"


@dataclass
class MatchingResult:
    """Result of matching a new record."""
    record_id: str
    matched_entity_id: Optional[str]
    confidence_score: float
    candidate_matches: List[Tuple[str, float]] = field(default_factory=list)  # (entity_id, score)
    decision: MatchDecision = MatchDecision.UNMATCHED
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user: Optional[str] = None
    notes: str = ""


@dataclass
class MatchingDecision:
    """User decision on a matching case."""
    case_id: str
    record_id: str
    decision: str  # 'match' or 'no_match' or 'entity_id'
    entity_id: Optional[str] = None
    user: Optional[str] = None
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""


class IncrementalMatcher:
    """
    Matcher for incremental entity matching.
    
    Matches new records against existing master entities,
    supporting auto-assignment, manual review, and override workflows.
    """
    
    def __init__(
        self,
        master_data_manager: MasterDataManager,
        auto_assign_threshold: float = 0.95,
        review_threshold: float = 0.70
    ):
        """
        Initialize incremental matcher.
        
        Args:
            master_data_manager: Manager with existing master entities
            auto_assign_threshold: Confidence needed for auto-assignment
            review_threshold: Minimum confidence to queue for review
        """
        self.master_data = master_data_manager
        self.auto_assign_threshold = auto_assign_threshold
        self.review_threshold = review_threshold
        
        # Default composite matching strategy
        self.matching_strategy = CompositeMatch([
            (ExactMatch(fields=['id']), 0.3),
            (FuzzyMatch(fields=['name', 'address'], threshold=0.8), 0.7)
        ])
        
        # Track all matching decisions
        self._matching_decisions: Dict[str, MatchingDecision] = {}
        self._queued_for_review: List[str] = []
        self._auto_assigned: Dict[str, str] = {}  # record_id -> entity_id
    
    def set_matching_strategy(self, strategy: MatchingStrategy) -> None:
        """Set custom matching strategy."""
        self.matching_strategy = strategy
    
    def match_against_existing(
        self,
        new_record: Dict[str, Any],
        entity_type: Optional[str] = None,
        top_k: int = 5
    ) -> MatchingResult:
        """
        Match a new record against existing master entities.
        
        Args:
            new_record: New record to match
            entity_type: Filter masters by entity type
            top_k: Number of top candidates to return
            
        Returns:
            MatchingResult with best matches
        """
        record_id = str(new_record.get('id', str(uuid.uuid4())))
        candidates: List[Tuple[str, float]] = []
        
        # Score against all master entities
        for entity_id, entity in self.master_data._entities.items():
            if entity_type and entity.entity_type != entity_type:
                continue
            
            # Score against canonical record
            score = self.matching_strategy.score(new_record, entity.canonical_record)
            if score >= self.review_threshold:
                candidates.append((entity_id, score))
        
        # Sort by confidence (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:top_k]
        
        # Determine decision
        result = MatchingResult(
            record_id=record_id,
            candidate_matches=top_candidates,
            confidence_score=top_candidates[0][1] if top_candidates else 0.0
        )
        
        if top_candidates:
            best_entity_id, best_score = top_candidates[0]
            
            if best_score >= self.auto_assign_threshold:
                result.matched_entity_id = best_entity_id
                result.decision = MatchDecision.AUTO_ASSIGNED
            elif best_score >= self.review_threshold:
                result.decision = MatchDecision.QUEUED_FOR_REVIEW
            else:
                result.decision = MatchDecision.UNMATCHED
        else:
            result.decision = MatchDecision.UNMATCHED
        
        return result
    
    def assign_to_entity(
        self,
        record_id: str,
        entity_id: str,
        new_record: Optional[Dict[str, Any]] = None,
        user: Optional[str] = None
    ) -> bool:
        """
        Assign new record to master entity.
        
        Args:
            record_id: Record ID
            entity_id: Master entity ID to assign to
            new_record: Record data (optional)
            user: User making assignment
            
        Returns:
            Success status
        """
        entity = self.master_data.get_master_entity(entity_id)
        if not entity:
            return False
        
        # If record provided, add to master entity
        if new_record:
            self.master_data.add_record_to_entity(entity_id, new_record)
        
        # Track decision
        self._auto_assigned[record_id] = entity_id
        self._matching_decisions[record_id] = MatchingDecision(
            case_id=str(uuid.uuid4()),
            record_id=record_id,
            decision='match',
            entity_id=entity_id,
            user=user or 'system'
        )
        
        return True
    
    def queue_for_review(
        self,
        record_id: str,
        candidate_matches: List[Tuple[str, float]],
        reason: str = ""
    ) -> bool:
        """
        Queue record for manual review.
        
        Args:
            record_id: Record ID
            candidate_matches: List of (entity_id, score) candidates
            reason: Reason for review
            
        Returns:
            Success status
        """
        if record_id in self._queued_for_review:
            return False
        
        self._queued_for_review.append(record_id)
        
        return True
    
    def get_review_queue(self) -> List[str]:
        """Get list of record IDs queued for review."""
        return self._queued_for_review.copy()
    
    def submit_matching_decision(
        self,
        record_id: str,
        decision: str,
        entity_id: Optional[str] = None,
        user: Optional[str] = None,
        confidence: float = 1.0,
        notes: str = ""
    ) -> bool:
        """
        Submit decision on queued matching case.
        
        Args:
            record_id: Record ID
            decision: 'match', 'no_match', or 'create_new'
            entity_id: Entity ID if matching
            user: User making decision
            confidence: Confidence in decision
            notes: Decision notes
            
        Returns:
            Success status
        """
        if record_id not in self._queued_for_review:
            return False
        
        case_id = str(uuid.uuid4())
        
        if decision == 'match' and entity_id:
            # Assign to entity
            self.assign_to_entity(record_id, entity_id, user=user)
            self._matching_decisions[record_id] = MatchingDecision(
                case_id=case_id,
                record_id=record_id,
                decision='match',
                entity_id=entity_id,
                user=user,
                confidence=confidence,
                notes=notes
            )
        elif decision == 'no_match' or decision == 'create_new':
            # Don't assign, will create new entity
            self._matching_decisions[record_id] = MatchingDecision(
                case_id=case_id,
                record_id=record_id,
                decision=decision,
                user=user,
                confidence=confidence,
                notes=notes
            )
        else:
            return False
        
        # Remove from queue
        self._queued_for_review.remove(record_id)
        
        return True
    
    def override_assignment(
        self,
        record_id: str,
        new_entity_id: str,
        user: Optional[str] = None,
        reason: str = ""
    ) -> bool:
        """
        Override previous matching decision.
        
        Args:
            record_id: Record ID
            new_entity_id: New entity to assign to
            user: User making override
            reason: Reason for override
            
        Returns:
            Success status
        """
        # Get or create matching decision
        old_decision = self._matching_decisions.get(record_id)
        old_entity_id = old_decision.entity_id if old_decision else None
        
        # Update assignment
        self._auto_assigned[record_id] = new_entity_id
        
        # Record override decision
        self._matching_decisions[record_id] = MatchingDecision(
            case_id=old_decision.case_id if old_decision else str(uuid.uuid4()),
            record_id=record_id,
            decision='match',
            entity_id=new_entity_id,
            user=user or 'system',
            confidence=1.0,
            notes=f"Override from {old_entity_id} - {reason}"
        )
        
        return True
    
    def get_assignment_for_record(self, record_id: str) -> Optional[str]:
        """Get entity ID that record is assigned to."""
        return self._auto_assigned.get(record_id)
    
    def get_matching_decision(self, record_id: str) -> Optional[MatchingDecision]:
        """Get matching decision for record."""
        return self._matching_decisions.get(record_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get matching statistics."""
        total_decisions = len(self._matching_decisions)
        
        auto_assigned = sum(
            1 for d in self._matching_decisions.values()
            if d.decision == 'match' and d.user == 'system'
        )
        
        manually_assigned = sum(
            1 for d in self._matching_decisions.values()
            if d.decision == 'match' and d.user != 'system'
        )
        
        return {
            'total_records_matched': total_decisions,
            'auto_assigned': auto_assigned,
            'manually_assigned': manually_assigned,
            'unmatched': sum(
                1 for d in self._matching_decisions.values()
                if d.decision in ['no_match', 'create_new']
            ),
            'queued_for_review': len(self._queued_for_review),
            'auto_assignment_rate': auto_assigned / total_decisions if total_decisions > 0 else 0.0
        }
    
    def create_batch_matches(
        self,
        records: List[Dict[str, Any]],
        entity_type: Optional[str] = None,
        auto_assign_only: bool = False
    ) -> Dict[str, MatchingResult]:
        """
        Match batch of records against existing masters.
        
        Args:
            records: List of records to match
            entity_type: Filter masters by entity type
            auto_assign_only: Only return high-confidence matches
            
        Returns:
            Mapping of record_id -> MatchingResult
        """
        results = {}
        
        for record in records:
            result = self.match_against_existing(record, entity_type)
            
            # Filter results if auto_assign_only
            if auto_assign_only and result.decision != MatchDecision.AUTO_ASSIGNED:
                continue
            
            results[result.record_id] = result
        
        return results
    
    def apply_batch_decisions(
        self,
        decisions: List[Dict[str, Any]],
        user: Optional[str] = None
    ) -> int:
        """
        Apply batch of matching decisions.
        
        Args:
            decisions: List of decisions with 'record_id', 'decision', 'entity_id'
            user: User applying decisions
            
        Returns:
            Number of decisions applied
        """
        applied = 0
        
        for decision in decisions:
            record_id = decision.get('record_id')
            decision_type = decision.get('decision')
            entity_id = decision.get('entity_id')
            notes = decision.get('notes', '')
            
            if record_id in self._queued_for_review:
                if self.submit_matching_decision(
                    record_id,
                    decision_type,
                    entity_id=entity_id,
                    user=user,
                    notes=notes
                ):
                    applied += 1
        
        return applied
