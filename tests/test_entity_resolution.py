"""
Comprehensive tests for entity resolution and deduplication system.

Tests cover:
- Matching strategies (exact, fuzzy, phonetic, geographic, temporal, semantic, composite)
- Deduplication engine with blocking
- Master data management and merging
- Incremental matching
- Review workflow
- Reconciliation
- Entity relationships
- Performance benchmarks
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from socrata_toolkit.entity.matching import (
    ExactMatch, FuzzyMatch, PhoneticMatch, GeographicMatch, TemporalMatch,
    SemanticMatch, CompositeMatch, MatchResult, MatchingStrategy
)
from socrata_toolkit.pipeline.dedupe import (
    Deduplicator, DeduplicationRule, DuplicateGroup, DuplicateStatus,
    MaterializationMode
)
from socrata_toolkit.core.master_data import (
    MasterDataManager, MasterEntity, EntityMergeStrategy
)
from socrata_toolkit.entity.blocking import (
    StandardBlocker, SortedNeighborhoodBlocker, SuffixArrayBlocker,
    CanopyBlocker, HybridBlocker
)
from socrata_toolkit.entity.incremental import (
    IncrementalMatcher, MatchDecision
)
from socrata_toolkit.entity.review import (
    ReviewWorkflow, ReviewCase, ReviewDecision, ReviewStatus
)
from socrata_toolkit.entity.reconciliation import (
    Reconciler, ExternalMasterLink, LinkStatus
)
from socrata_toolkit.entity.relationships import (
    RelationshipGraph, RelationshipType, EntityRelationship
)


# ========== MATCHING STRATEGY TESTS ==========

class TestExactMatch:
    """Tests for ExactMatch strategy."""
    
    def test_exact_match_identical(self):
        """Test exact match with identical records."""
        matcher = ExactMatch(fields=['id', 'name'])
        record1 = {'id': '1', 'name': 'John Doe', 'age': 30}
        record2 = {'id': '1', 'name': 'John Doe', 'age': 25}
        
        score = matcher.score(record1, record2)
        assert score == 1.0
    
    def test_exact_match_partial(self):
        """Test exact match with partial matches."""
        matcher = ExactMatch(
            fields=['id', 'name'],
            field_weights={'id': 0.6, 'name': 0.4}
        )
        record1 = {'id': '1', 'name': 'John'}
        record2 = {'id': '1', 'name': 'Jane'}
        
        score = matcher.score(record1, record2)
        assert 0.5 < score < 1.0
    
    def test_exact_match_case_insensitive(self):
        """Test case-insensitive matching."""
        matcher = ExactMatch(fields=['name'], case_sensitive=False)
        record1 = {'name': 'JOHN DOE'}
        record2 = {'name': 'john doe'}
        
        score = matcher.score(record1, record2)
        assert score == 1.0
    
    def test_exact_match_no_match(self):
        """Test no match."""
        matcher = ExactMatch(fields=['id'])
        record1 = {'id': '1'}
        record2 = {'id': '2'}
        
        score = matcher.score(record1, record2)
        assert score == 0.0


class TestFuzzyMatch:
    """Tests for FuzzyMatch strategy."""
    
    def test_fuzzy_match_typo(self):
        """Test fuzzy match with typos."""
        matcher = FuzzyMatch(fields=['name'], threshold=0.8)
        record1 = {'name': 'John Doe'}
        record2 = {'name': 'Jon Doe'}
        
        score = matcher.score(record1, record2)
        assert score > 0.8
    
    def test_fuzzy_match_word_order(self):
        """Test token set ratio with word order variations."""
        matcher = FuzzyMatch(
            fields=['address'],
            algorithm='token_set_ratio'
        )
        record1 = {'address': '123 Main Street New York'}
        record2 = {'address': '123 New York Main Street'}
        
        score = matcher.score(record1, record2)
        assert score > 0.7


class TestPhoneticMatch:
    """Tests for PhoneticMatch strategy."""
    
    def test_phonetic_match_soundex(self):
        """Test phonetic matching with similar sounding names."""
        matcher = PhoneticMatch(fields=['name'])
        record1 = {'name': 'Smith'}
        record2 = {'name': 'Smythe'}
        
        score = matcher.score(record1, record2)
        assert score > 0.5


class TestGeographicMatch:
    """Tests for GeographicMatch strategy."""
    
    def test_geographic_match_within_threshold(self):
        """Test geographic matching within distance threshold."""
        matcher = GeographicMatch(
            lat_field='latitude',
            lon_field='longitude',
            distance_threshold_m=20.0
        )
        record1 = {'latitude': 40.7128, 'longitude': -74.0060}
        record2 = {'latitude': 40.7129, 'longitude': -74.0061}
        
        score = matcher.score(record1, record2)
        assert score > 0.9
    
    def test_geographic_match_outside_threshold(self):
        """Test geographic matching outside distance threshold."""
        matcher = GeographicMatch(distance_threshold_m=10.0)
        record1 = {'latitude': 40.7128, 'longitude': -74.0060}
        record2 = {'latitude': 40.8, 'longitude': -74.0}
        
        score = matcher.score(record1, record2)
        assert score == 0.0


class TestTemporalMatch:
    """Tests for TemporalMatch strategy."""
    
    def test_temporal_match_overlapping_ranges(self):
        """Test matching overlapping date ranges."""
        matcher = TemporalMatch(
            start_field='start_date',
            end_field='end_date'
        )
        record1 = {
            'start_date': '2024-01-01',
            'end_date': '2024-03-31'
        }
        record2 = {
            'start_date': '2024-02-01',
            'end_date': '2024-04-30'
        }
        
        score = matcher.score(record1, record2)
        assert score == 1.0


class TestCompositeMatch:
    """Tests for CompositeMatch strategy."""
    
    def test_composite_match_weighted(self):
        """Test composite matching with multiple strategies."""
        exact = ExactMatch(fields=['id'], threshold=1.0)
        fuzzy = FuzzyMatch(fields=['name'], threshold=0.8)
        
        composite = CompositeMatch([
            (exact, 0.4),
            (fuzzy, 0.6)
        ])
        
        record1 = {'id': '1', 'name': 'John Doe'}
        record2 = {'id': '1', 'name': 'Jon Doe'}
        
        score = composite.score(record1, record2)
        assert score > 0.8


# ========== DEDUPLICATION TESTS ==========

class TestDeduplicator:
    """Tests for Deduplicator engine."""
    
    def test_find_duplicates(self):
        """Test finding duplicates with blocking."""
        dedup = Deduplicator()
        records = [
            {'id': '1', 'name': 'John Doe', 'borough': 'Manhattan'},
            {'id': '2', 'name': 'John Doe', 'borough': 'Manhattan'},
            {'id': '3', 'name': 'Jane Smith', 'borough': 'Brooklyn'},
        ]
        
        rule = DeduplicationRule(
            rule_id='test_rule',
            entity_type='person',
            matching_strategy=ExactMatch(fields=['name']),
            threshold=1.0,
            blocking_keys=['borough']
        )
        
        groups = dedup.find_duplicates(records, rule)
        assert len(groups) > 0
    
    def test_manual_duplicate_marking(self):
        """Test manually marking records as duplicates."""
        dedup = Deduplicator()
        
        success = dedup.mark_as_duplicates(
            ['rec1', 'rec2', 'rec3'],
            canonical_id='rec1',
            reason='Manually identified'
        )
        
        assert success
        assert dedup.get_duplicates_for_record('rec2') == ['rec1', 'rec3']


# ========== MASTER DATA TESTS ==========

class TestMasterDataManager:
    """Tests for MasterDataManager."""
    
    def test_create_master_entity(self):
        """Test creating master entity from sources."""
        mgr = MasterDataManager()
        
        record1 = {'id': '1', 'name': 'John Doe', 'address': '123 Main St'}
        record2 = {'id': '2', 'name': 'John Doe', 'address': '123 Main Street'}
        
        entity_id = mgr.create_master_entity(
            record1, record2,
            entity_type='person',
            merge_strategy=EntityMergeStrategy.PICK_FIRST
        )
        
        assert entity_id is not None
        entity = mgr.get_master_entity(entity_id)
        assert entity is not None
        assert len(entity.source_record_ids) == 2
    
    def test_merge_pick_latest(self):
        """Test merge using PICK_LATEST strategy."""
        mgr = MasterDataManager()
        
        record1 = {'id': '1', 'name': 'John', 'status': 'inactive'}
        record2 = {'id': '2', 'name': 'John', 'status': 'active'}
        
        entity_id = mgr.create_master_entity(
            record1, record2,
            entity_type='person',
            merge_strategy=EntityMergeStrategy.PICK_LATEST
        )
        
        entity = mgr.get_master_entity(entity_id)
        assert entity.canonical_record['status'] == 'active'
    
    def test_validate_merge(self):
        """Test merge validation."""
        mgr = MasterDataManager()
        
        entity_id = mgr.create_master_entity(
            {'id': '1', 'name': 'John', 'email': 'john@example.com'},
            entity_type='person'
        )
        
        is_valid, issues = mgr.validate_merge(
            entity_id,
            required_fields=['name', 'email']
        )
        
        assert is_valid


# ========== BLOCKING TESTS ==========

class TestStandardBlocker:
    """Tests for StandardBlocker."""
    
    def test_blocking_reduces_pairs(self):
        """Test that blocking reduces candidate pairs."""
        records = [
            {'id': '1', 'borough': 'Manhattan', 'name': 'John'},
            {'id': '2', 'borough': 'Manhattan', 'name': 'Jane'},
            {'id': '3', 'borough': 'Brooklyn', 'name': 'Bob'},
            {'id': '4', 'borough': 'Brooklyn', 'name': 'Alice'},
        ]
        
        blocker = StandardBlocker(blocking_keys=['borough'])
        pairs = blocker.create_candidate_pairs(records)
        
        # Should only have pairs within blocks
        assert len(pairs) == 2  # 1 pair from Manhattan, 1 pair from Brooklyn
        
        stats = blocker.get_statistics()
        assert stats.reduction_ratio > 0.5


# ========== INCREMENTAL MATCHING TESTS ==========

class TestIncrementalMatcher:
    """Tests for IncrementalMatcher."""
    
    def test_match_new_record_auto_assign(self):
        """Test auto-assignment of new record."""
        mgr = MasterDataManager()
        matcher = IncrementalMatcher(
            mgr,
            auto_assign_threshold=0.95
        )
        
        # Create master
        mgr.create_master_entity(
            {'id': 'master_1', 'name': 'John Doe'},
            entity_type='person'
        )
        
        # Match new record
        matcher.set_matching_strategy(ExactMatch(fields=['name']))
        new_record = {'id': 'new_1', 'name': 'John Doe'}
        result = matcher.match_against_existing(new_record)
        
        assert result.decision == MatchDecision.AUTO_ASSIGNED


# ========== REVIEW WORKFLOW TESTS ==========

class TestReviewWorkflow:
    """Tests for ReviewWorkflow."""
    
    def test_add_and_review_case(self):
        """Test adding and reviewing a case."""
        workflow = ReviewWorkflow()
        
        case = ReviewCase(
            record1={'id': '1', 'name': 'John Doe'},
            record2={'id': '2', 'name': 'Jon Doe'},
            matching_score=0.85
        )
        
        case_id = workflow.add_case(case)
        
        # Submit decision
        success = workflow.submit_decision(
            case_id,
            ReviewDecision.MATCH,
            reviewer='reviewer1',
            notes='Names are similar'
        )
        
        assert success
        
        # Check statistics
        stats = workflow.get_statistics()
        assert stats.completed_cases == 1
    
    def test_reviewer_metrics(self):
        """Test reviewer performance metrics."""
        workflow = ReviewWorkflow()
        
        # Add and review multiple cases
        for i in range(5):
            case = ReviewCase(
                record1={'id': f'1_{i}'}, 
                record2={'id': f'2_{i}'},
                matching_score=0.8
            )
            case_id = workflow.add_case(case)
            workflow.assign_case(case_id, 'reviewer1')
            workflow.submit_decision(
                case_id,
                ReviewDecision.MATCH,
                reviewer='reviewer1'
            )
        
        metrics = workflow.get_reviewer_metrics('reviewer1')
        assert metrics['total_reviewed'] == 5
        assert metrics['match_rate'] == 100.0


# ========== RECONCILIATION TESTS ==========

class TestReconciler:
    """Tests for Reconciler."""
    
    def test_reconcile_with_external(self):
        """Test reconciliation with external master."""
        mgr = MasterDataManager()
        reconciler = Reconciler(mgr)
        
        # Create local masters
        mgr.create_master_entity(
            {'id': 'local_1', 'name': 'John Doe', 'borough': 'Manhattan'},
            entity_type='person'
        )
        
        # Import external
        external_data = [
            {'id': 'ext_1', 'name': 'John Doe', 'borough': 'Manhattan'}
        ]
        reconciler.import_external_master('NYC_CARTO', external_data)
        
        # Reconcile
        report = reconciler.reconcile_to_external('NYC_CARTO')
        assert report.matched_count > 0


# ========== RELATIONSHIP TESTS ==========

class TestRelationshipGraph:
    """Tests for RelationshipGraph."""
    
    def test_add_relationship(self):
        """Test adding relationships."""
        graph = RelationshipGraph()
        
        rel_id = graph.add_relationship(
            'block_1',
            'segment_1',
            RelationshipType.CONTAINS
        )
        
        assert rel_id is not None
        rel = graph.get_relationship(rel_id)
        assert rel.source_entity_id == 'block_1'
    
    def test_find_related_entities(self):
        """Test finding related entities."""
        graph = RelationshipGraph()
        
        graph.add_relationship('block_1', 'segment_1', RelationshipType.CONTAINS)
        graph.add_relationship('block_1', 'segment_2', RelationshipType.CONTAINS)
        
        related = graph.get_related_entities('block_1', RelationshipType.CONTAINS)
        assert len(related) == 2
    
    def test_find_path(self):
        """Test finding path between entities."""
        graph = RelationshipGraph()
        
        graph.add_relationship('street_1', 'block_1', RelationshipType.CONTAINS)
        graph.add_relationship('block_1', 'segment_1', RelationshipType.CONTAINS)
        
        path = graph.find_path('street_1', 'segment_1')
        assert path is not None
        assert len(path) == 3


# ========== PERFORMANCE BENCHMARKS ==========

class TestPerformanceBenchmarks:
    """Performance tests for large datasets."""
    
    @pytest.mark.slow
    def test_dedup_1000_records(self):
        """Benchmark deduplication on 1000 records."""
        import time
        import random
        
        # Generate test records
        records = []
        for i in range(1000):
            borough = random.choice(['Manhattan', 'Brooklyn', 'Queens'])
            records.append({
                'id': str(i),
                'name': f'Entity {i // 10}',  # Duplicates
                'borough': borough,
                'address': f'{i} Main Street'
            })
        
        dedup = Deduplicator()
        rule = DeduplicationRule(
            rule_id='perf_test',
            entity_type='entity',
            matching_strategy=FuzzyMatch(fields=['name'], threshold=0.9),
            blocking_keys=['borough'],
            threshold=0.9
        )
        
        start = time.time()
        result = dedup.apply_rule(records, rule)
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert elapsed < 30.0
        print(f"1000 records deduplicated in {elapsed:.2f}s")
    
    @pytest.mark.slow
    def test_blocking_efficiency(self):
        """Test blocking algorithm efficiency."""
        import time
        
        # Generate 10K records
        records = [
            {
                'id': str(i),
                'borough': f'borough_{i % 20}',
                'name': f'Name {i}',
                'block': f'block_{i % 100}'
            }
            for i in range(10000)
        ]
        
        blocker = StandardBlocker(blocking_keys=['borough', 'block'])
        
        start = time.time()
        pairs = blocker.create_candidate_pairs(records)
        elapsed = time.time() - start
        
        stats = blocker.get_statistics()
        
        # Should dramatically reduce pairs
        assert stats.reduction_ratio > 0.95
        assert elapsed < 5.0
        print(f"Reduced {stats.total_possible_pairs} to {stats.candidate_pairs} pairs in {elapsed:.2f}s")


# ========== INTEGRATION TESTS ==========

class TestEndToEndFlow:
    """End-to-end integration tests."""
    
    def test_complete_deduplication_workflow(self):
        """Test complete deduplication and master creation workflow."""
        # Setup
        dedup = Deduplicator()
        mgr = MasterDataManager()
        
        records = [
            {'id': '1', 'name': 'John Doe', 'address': '123 Main'},
            {'id': '2', 'name': 'John Doe', 'address': '123 Main Street'},
            {'id': '3', 'name': 'Jane Smith', 'address': '456 Oak'},
        ]
        
        # Find duplicates
        rule = DeduplicationRule(
            rule_id='test',
            entity_type='person',
            matching_strategy=FuzzyMatch(fields=['name', 'address'], threshold=0.8),
            blocking_keys=['name'],
            threshold=0.8
        )
        
        groups = dedup.find_duplicates(records, rule)
        assert len(groups) > 0
        
        # Create master entities from groups
        for group in groups:
            source_records = [
                records[int(rid)]
                for rid in group.duplicate_record_ids
                if rid.isdigit()
            ]
            
            if source_records:
                entity_id = mgr.create_master_entity(
                    *source_records,
                    entity_type='person'
                )
                
                assert entity_id is not None
        
        # Verify
        stats = mgr.get_statistics()
        assert stats['total_entities'] > 0


# ========== EDGE CASE TESTS ==========

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_records(self):
        """Test handling empty records."""
        dedup = Deduplicator()
        rule = DeduplicationRule(
            rule_id='test',
            entity_type='test',
            matching_strategy=ExactMatch(fields=['id'])
        )
        
        groups = dedup.find_duplicates([], rule)
        assert len(groups) == 0
    
    def test_null_field_values(self):
        """Test handling null field values."""
        matcher = FuzzyMatch(fields=['name', 'address'])
        
        record1 = {'name': 'John', 'address': None}
        record2 = {'name': 'John', 'address': '123 Main'}
        
        score = matcher.score(record1, record2)
        assert score >= 0.0  # Should not crash
    
    def test_special_characters(self):
        """Test handling special characters."""
        matcher = FuzzyMatch(fields=['name'])
        
        record1 = {'name': "O'Brien"}
        record2 = {'name': "Obrien"}
        
        score = matcher.score(record1, record2)
        assert score > 0.5


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
