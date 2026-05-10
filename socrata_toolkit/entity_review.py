"""
Manual review workflow for entity resolution decisions.

Provides interface for human reviewers to validate, override,
and fine-tune automated matching decisions.

Example:
    >>> from socrata_toolkit.entity_review import ReviewWorkflow, ReviewCase
    >>> workflow = ReviewWorkflow()
    >>> case = ReviewCase(
    ...     record1={'id': '1', 'name': 'John Doe'},
    ...     record2={'id': '2', 'name': 'Jon Doe'},
    ...     matching_score=0.85
    ... )
    >>> workflow.add_case(case)
    >>> cases = workflow.get_unreviewed_cases()
    >>> workflow.submit_decision(case_id, decision='MATCH', user='reviewer1')
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .entity_matching import MatchingStrategy


class ReviewDecision(str, Enum):
    """Decision on a matching case."""
    MATCH = "match"
    NOT_MATCH = "not_match"
    UNSURE = "unsure"
    SKIP = "skip"


class ReviewStatus(str, Enum):
    """Status of a review case."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISPUTED = "disputed"


@dataclass
class FieldComparison:
    """Comparison of a single field between two records."""
    field_name: str
    value1: Any
    value2: Any
    match_score: float
    is_match: bool


@dataclass
class ReviewCase:
    """
    A case for manual review.
    
    Represents two records that need human review to determine
    if they should be considered duplicates.
    """
    case_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    record1: Dict[str, Any] = field(default_factory=dict)
    record2: Dict[str, Any] = field(default_factory=dict)
    matching_score: float = 0.0
    strategy_name: str = ""
    
    # Field-level details
    fields_compared: Dict[str, FieldComparison] = field(default_factory=dict)
    
    # Review metadata
    status: ReviewStatus = ReviewStatus.PENDING
    decision: Optional[ReviewDecision] = None
    reviewer: Optional[str] = None
    review_timestamp: Optional[datetime] = None
    notes: str = ""
    time_to_review_seconds: float = 0.0
    
    # Audit
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __repr__(self) -> str:
        return (f"ReviewCase(case_id={self.case_id}, status={self.status.value}, "
                f"decision={self.decision}, reviewer={self.reviewer})")


@dataclass
class ReviewStatistics:
    """Statistics on review workflow."""
    total_cases: int
    pending_cases: int
    completed_cases: int
    match_rate: float  # Percentage reviewed as matches
    avg_review_time_seconds: float
    reviewers: List[str]
    agreement_with_auto: float  # Agreement rate with automated decisions


class ReviewWorkflow:
    """
    Manages manual review workflow for entity matching.
    
    Tracks review cases, decisions, and provides metrics
    on reviewer performance and automation accuracy.
    """
    
    def __init__(self):
        """Initialize review workflow."""
        self._cases: Dict[str, ReviewCase] = {}
        self._case_order: List[str] = []  # Insertion order
        self._reviewer_assignments: Dict[str, List[str]] = {}  # reviewer -> case_ids
        self._decision_history: List[Dict[str, Any]] = []
    
    def add_case(self, case: ReviewCase) -> str:
        """
        Add a case for review.
        
        Args:
            case: ReviewCase to add
            
        Returns:
            Case ID
        """
        self._cases[case.case_id] = case
        self._case_order.append(case.case_id)
        return case.case_id
    
    def add_cases_batch(self, cases: List[ReviewCase]) -> List[str]:
        """Add multiple cases for review."""
        case_ids = []
        for case in cases:
            case_ids.append(self.add_case(case))
        return case_ids
    
    def get_case(self, case_id: str) -> Optional[ReviewCase]:
        """Get a review case by ID."""
        return self._cases.get(case_id)
    
    def get_unreviewed_cases(self) -> List[ReviewCase]:
        """Get all unreviewed cases."""
        return [
            self._cases[cid]
            for cid in self._case_order
            if self._cases[cid].status == ReviewStatus.PENDING
        ]
    
    def get_pending_cases_for_reviewer(self, reviewer: str) -> List[ReviewCase]:
        """Get pending cases assigned to reviewer."""
        case_ids = self._reviewer_assignments.get(reviewer, [])
        return [
            self._cases[cid]
            for cid in case_ids
            if self._cases[cid].status in [ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS]
        ]
    
    def get_completed_cases_for_reviewer(self, reviewer: str) -> List[ReviewCase]:
        """Get completed cases reviewed by reviewer."""
        case_ids = self._reviewer_assignments.get(reviewer, [])
        return [
            self._cases[cid]
            for cid in case_ids
            if self._cases[cid].status == ReviewStatus.COMPLETED
        ]
    
    def assign_case(self, case_id: str, reviewer: str) -> bool:
        """
        Assign case to reviewer.
        
        Args:
            case_id: Case ID
            reviewer: Reviewer username
            
        Returns:
            Success status
        """
        case = self._cases.get(case_id)
        if not case:
            return False
        
        case.status = ReviewStatus.IN_PROGRESS
        
        if reviewer not in self._reviewer_assignments:
            self._reviewer_assignments[reviewer] = []
        
        if case_id not in self._reviewer_assignments[reviewer]:
            self._reviewer_assignments[reviewer].append(case_id)
        
        return True
    
    def assign_cases_batch(
        self,
        case_ids: List[str],
        reviewer: str
    ) -> int:
        """Assign multiple cases to reviewer."""
        assigned = 0
        for case_id in case_ids:
            if self.assign_case(case_id, reviewer):
                assigned += 1
        return assigned
    
    def submit_decision(
        self,
        case_id: str,
        decision: ReviewDecision,
        reviewer: str,
        notes: str = ""
    ) -> bool:
        """
        Submit review decision.
        
        Args:
            case_id: Case ID
            decision: MATCH, NOT_MATCH, UNSURE, or SKIP
            reviewer: Reviewer username
            notes: Optional review notes
            
        Returns:
            Success status
        """
        case = self._cases.get(case_id)
        if not case:
            return False
        
        now = datetime.utcnow()
        case.decision = decision
        case.reviewer = reviewer
        case.review_timestamp = now
        case.notes = notes
        case.time_to_review_seconds = (now - case.created_at).total_seconds()
        
        if decision != ReviewDecision.SKIP:
            case.status = ReviewStatus.COMPLETED
        
        # Record decision
        self._decision_history.append({
            'case_id': case_id,
            'decision': decision.value,
            'reviewer': reviewer,
            'timestamp': now.isoformat(),
            'time_to_review': case.time_to_review_seconds,
            'notes': notes
        })
        
        return True
    
    def dispute_decision(
        self,
        case_id: str,
        reason: str,
        disputed_by: str
    ) -> bool:
        """
        Mark a completed review as disputed.
        
        Args:
            case_id: Case ID
            reason: Reason for dispute
            disputed_by: User disputing decision
            
        Returns:
            Success status
        """
        case = self._cases.get(case_id)
        if not case or case.status != ReviewStatus.COMPLETED:
            return False
        
        case.status = ReviewStatus.DISPUTED
        case.notes += f"\nDisputed by {disputed_by}: {reason}"
        
        return True
    
    def override_decision(
        self,
        case_id: str,
        new_decision: ReviewDecision,
        user: str,
        reason: str
    ) -> bool:
        """
        Override a previous review decision.
        
        Args:
            case_id: Case ID
            new_decision: New decision
            user: User making override
            reason: Reason for override
            
        Returns:
            Success status
        """
        case = self._cases.get(case_id)
        if not case:
            return False
        
        old_decision = case.decision
        old_reviewer = case.reviewer
        
        # Update decision
        case.decision = new_decision
        case.status = ReviewStatus.COMPLETED
        case.reviewer = user
        case.review_timestamp = datetime.utcnow()
        case.notes += f"\nOverridden by {user} (was {old_decision} by {old_reviewer}): {reason}"
        
        return True
    
    def get_statistics(self) -> ReviewStatistics:
        """Get review workflow statistics."""
        cases = list(self._cases.values())
        
        if not cases:
            return ReviewStatistics(
                total_cases=0,
                pending_cases=0,
                completed_cases=0,
                match_rate=0.0,
                avg_review_time_seconds=0.0,
                reviewers=[],
                agreement_with_auto=0.0
            )
        
        pending = sum(1 for c in cases if c.status == ReviewStatus.PENDING)
        completed = sum(1 for c in cases if c.status == ReviewStatus.COMPLETED)
        
        matches = sum(
            1 for c in cases
            if c.decision == ReviewDecision.MATCH
        )
        match_rate = (matches / completed * 100) if completed > 0 else 0.0
        
        # Average review time
        reviewed = [c for c in cases if c.review_timestamp is not None]
        avg_time = (
            sum(c.time_to_review_seconds for c in reviewed) / len(reviewed)
            if reviewed else 0.0
        )
        
        reviewers = list(self._reviewer_assignments.keys())
        
        return ReviewStatistics(
            total_cases=len(cases),
            pending_cases=pending,
            completed_cases=completed,
            match_rate=match_rate,
            avg_review_time_seconds=avg_time,
            reviewers=reviewers,
            agreement_with_auto=self._calculate_auto_agreement()
        )
    
    def _calculate_auto_agreement(self) -> float:
        """Calculate agreement rate with automated decisions."""
        reviewed = [c for c in self._cases.values() if c.review_timestamp is not None]
        
        if not reviewed:
            return 0.0
        
        # If score > 0.85 and review is MATCH, or score < 0.85 and review is NOT_MATCH,
        # that's agreement
        agreements = 0
        for case in reviewed:
            auto_would_match = case.matching_score >= 0.85
            human_matched = case.decision == ReviewDecision.MATCH
            
            if auto_would_match == human_matched:
                agreements += 1
        
        return (agreements / len(reviewed) * 100) if reviewed else 0.0
    
    def export_review_log(self) -> List[Dict[str, Any]]:
        """
        Export review log as list of dicts.
        
        Returns:
            List of review records
        """
        exported = []
        
        for case in self._cases.values():
            record = {
                'case_id': case.case_id,
                'record1_id': str(case.record1.get('id', '')),
                'record2_id': str(case.record2.get('id', '')),
                'matching_score': case.matching_score,
                'strategy': case.strategy_name,
                'status': case.status.value,
                'decision': case.decision.value if case.decision else None,
                'reviewer': case.reviewer,
                'review_timestamp': case.review_timestamp.isoformat() if case.review_timestamp else None,
                'time_to_review_seconds': case.time_to_review_seconds,
                'notes': case.notes,
                'created_at': case.created_at.isoformat()
            }
            exported.append(record)
        
        return exported
    
    def import_decisions(self, decisions: List[Dict[str, Any]]) -> int:
        """
        Import review decisions from external source.
        
        Args:
            decisions: List of decision dicts
            
        Returns:
            Number imported
        """
        imported = 0
        
        for decision in decisions:
            case_id = decision.get('case_id')
            case = self._cases.get(case_id)
            
            if not case:
                continue
            
            try:
                decision_type = ReviewDecision(decision.get('decision', 'unsure'))
                if self.submit_decision(
                    case_id,
                    decision_type,
                    decision.get('reviewer', 'imported'),
                    decision.get('notes', '')
                ):
                    imported += 1
            except ValueError:
                continue
        
        return imported
    
    def get_reviewer_metrics(self, reviewer: str) -> Dict[str, Any]:
        """Get metrics for a specific reviewer."""
        case_ids = self._reviewer_assignments.get(reviewer, [])
        cases = [self._cases[cid] for cid in case_ids if cid in self._cases]
        
        if not cases:
            return {
                'reviewer': reviewer,
                'total_reviewed': 0,
                'match_rate': 0.0,
                'avg_review_time': 0.0,
                'accuracy_vs_auto': 0.0
            }
        
        reviewed = [c for c in cases if c.status == ReviewStatus.COMPLETED]
        
        matches = sum(1 for c in reviewed if c.decision == ReviewDecision.MATCH)
        match_rate = (matches / len(reviewed) * 100) if reviewed else 0.0
        
        avg_time = (
            sum(c.time_to_review_seconds for c in reviewed) / len(reviewed)
            if reviewed else 0.0
        )
        
        # Calculate accuracy vs automated
        auto_agreements = 0
        for case in reviewed:
            auto_would_match = case.matching_score >= 0.85
            human_matched = case.decision == ReviewDecision.MATCH
            if auto_would_match == human_matched:
                auto_agreements += 1
        
        accuracy = (auto_agreements / len(reviewed) * 100) if reviewed else 0.0
        
        return {
            'reviewer': reviewer,
            'total_reviewed': len(reviewed),
            'match_rate': match_rate,
            'avg_review_time_seconds': avg_time,
            'accuracy_vs_auto': accuracy
        }
    
    def get_disputed_cases(self) -> List[ReviewCase]:
        """Get all disputed review cases."""
        return [
            self._cases[cid]
            for cid in self._case_order
            if self._cases[cid].status == ReviewStatus.DISPUTED
        ]
