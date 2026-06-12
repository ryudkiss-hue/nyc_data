"""Tests for entity.blocking module - blocking algorithms for entity resolution."""
from __future__ import annotations

import pytest

from socrata_toolkit.entity.blocking import (
    BlockingAlgorithm,
    BlockStatistics,
    CanopyBlocker,
    HybridBlocker,
    SortedNeighborhoodBlocker,
    StandardBlocker,
    SuffixArrayBlocker,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def nyc_records():
    """Representative NYC DOT SIM records for blocking tests."""
    return [
        {"id": "1", "borough": "MANHATTAN", "block_id": "1001", "address": "123 Broadway"},
        {"id": "2", "borough": "MANHATTAN", "block_id": "1001", "address": "125 Broadway"},
        {"id": "3", "borough": "MANHATTAN", "block_id": "1002", "address": "500 Fifth Ave"},
        {"id": "4", "borough": "BROOKLYN", "block_id": "2001", "address": "45 Atlantic Ave"},
        {"id": "5", "borough": "BROOKLYN", "block_id": "2001", "address": "47 Atlantic Avenue"},
        {"id": "6", "borough": "QUEENS", "block_id": "3001", "address": "11-15 Jamaica Ave"},
    ]

@pytest.fixture
def small_records():
    """Minimal three-record set for pair-count assertions."""
    return [
        {"id": "A", "borough": "MN", "name": "Alice"},
        {"id": "B", "borough": "MN", "name": "Bob"},
        {"id": "C", "borough": "BK", "name": "Carol"},
    ]

# ---------------------------------------------------------------------------
# BlockStatistics tests
# ---------------------------------------------------------------------------

class TestBlockStatistics:
    """Tests for the BlockStatistics dataclass."""

    def test_construction(self):
        """BlockStatistics should store all provided fields."""
        stats = BlockStatistics(
            total_records=100,
            total_possible_pairs=4950,
            candidate_pairs=50,
            reduction_ratio=0.99,
            largest_block_size=10,
            blocks_created=20,
            empty_blocks=0,
        )
        assert stats.total_records == 100
        assert stats.total_possible_pairs == 4950
        assert stats.candidate_pairs == 50
        assert stats.reduction_ratio == pytest.approx(0.99)
        assert stats.largest_block_size == 10
        assert stats.blocks_created == 20
        assert stats.empty_blocks == 0

# ---------------------------------------------------------------------------
# StandardBlocker tests
# ---------------------------------------------------------------------------

class TestStandardBlocker:
    """Tests for StandardBlocker algorithm."""

    def test_pairs_within_same_block(self, small_records):
        """Records with the same blocking key should be paired."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        pairs = blocker.create_candidate_pairs(small_records)
        assert (0, 1) in pairs

    def test_no_cross_block_pairs(self, small_records):
        """Records in different blocks should not be paired."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        pairs = blocker.create_candidate_pairs(small_records)
        cross_pairs = [(i, j) for (i, j) in pairs if i in (0, 1) and j == 2]
        assert cross_pairs == []

    def test_pair_count_single_block(self):
        """Four records in the same block should produce six pairs (4 choose 2)."""
        records = [{"borough": "MN", "id": str(i)} for i in range(4)]
        blocker = StandardBlocker(blocking_keys=["borough"])
        pairs = blocker.create_candidate_pairs(records)
        assert len(pairs) == 6

    def test_empty_records_returns_empty_pairs(self):
        """Empty input should produce no pairs."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        pairs = blocker.create_candidate_pairs([])
        assert pairs == []

    def test_single_record_returns_empty_pairs(self):
        """A single record has no possible pairs."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        pairs = blocker.create_candidate_pairs([{"borough": "MN", "id": "1"}])
        assert pairs == []

    def test_statistics_populated_after_call(self, nyc_records):
        """Statistics should be set after create_candidate_pairs is called."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        blocker.create_candidate_pairs(nyc_records)
        stats = blocker.get_statistics()
        assert stats is not None
        assert stats.total_records == len(nyc_records)
        assert stats.candidate_pairs >= 0

    def test_statistics_initially_none(self):
        """Statistics should be None before any call to create_candidate_pairs."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        assert blocker.get_statistics() is None

    def test_reduction_ratio_less_than_one(self, nyc_records):
        """Reduction ratio should be less than 1.0 for a realistic dataset."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        blocker.create_candidate_pairs(nyc_records)
        stats = blocker.get_statistics()
        assert stats.reduction_ratio < 1.0

    def test_multi_key_blocking(self, nyc_records):
        """Multiple blocking keys should reduce candidate pairs further."""
        single_key = StandardBlocker(blocking_keys=["borough"])
        multi_key = StandardBlocker(blocking_keys=["borough", "block_id"])

        single_pairs = single_key.create_candidate_pairs(nyc_records)
        multi_pairs = multi_key.create_candidate_pairs(nyc_records)
        assert len(multi_pairs) <= len(single_pairs)

    def test_missing_blocking_key_grouped_together(self):
        """Records missing the blocking key should be grouped under __none__."""
        records = [
            {"id": "1"},
            {"id": "2"},
            {"id": "3", "borough": "MN"},
        ]
        blocker = StandardBlocker(blocking_keys=["borough"])
        pairs = blocker.create_candidate_pairs(records)
        assert (0, 1) in pairs

    def test_blocking_key_normalised_case(self):
        """Blocking key values should be case-normalised to group correctly."""
        records = [
            {"borough": "Manhattan"},
            {"borough": "MANHATTAN"},
            {"borough": "brooklyn"},
        ]
        blocker = StandardBlocker(blocking_keys=["borough"])
        pairs = blocker.create_candidate_pairs(records)
        assert (0, 1) in pairs

    def test_all_pairs_indices_in_bounds(self, nyc_records):
        """All pair indices should be valid indices into the records list."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        pairs = blocker.create_candidate_pairs(nyc_records)
        n = len(nyc_records)
        for i, j in pairs:
            assert 0 <= i < n
            assert 0 <= j < n

    def test_pairs_are_ordered(self, nyc_records):
        """Each pair should have i < j to avoid duplicates."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        pairs = blocker.create_candidate_pairs(nyc_records)
        for i, j in pairs:
            assert i < j

# ---------------------------------------------------------------------------
# SortedNeighborhoodBlocker tests
# ---------------------------------------------------------------------------

class TestSortedNeighborhoodBlocker:
    """Tests for SortedNeighborhoodBlocker algorithm."""

    def test_window_size_enforced_minimum(self):
        """Window size below 2 should be clamped to 2."""
        blocker = SortedNeighborhoodBlocker(blocking_keys=["borough"], window_size=0)
        assert blocker.window_size == 2

    def test_pairs_created_within_window(self, nyc_records):
        """Records within the sort window should be candidate pairs."""
        blocker = SortedNeighborhoodBlocker(blocking_keys=["borough"], window_size=3)
        pairs = blocker.create_candidate_pairs(nyc_records)
        assert len(pairs) > 0

    def test_large_window_returns_all_pairs(self):
        """A window equal to n should include all possible pairs."""
        records = [{"borough": f"boro-{i}"} for i in range(5)]
        blocker = SortedNeighborhoodBlocker(blocking_keys=["borough"], window_size=100)
        pairs = blocker.create_candidate_pairs(records)
        max_pairs = len(records) * (len(records) - 1) // 2
        assert len(pairs) == max_pairs

    def test_no_duplicate_pairs(self, nyc_records):
        """The returned pairs should have no duplicates."""
        blocker = SortedNeighborhoodBlocker(blocking_keys=["borough"], window_size=4)
        pairs = blocker.create_candidate_pairs(nyc_records)
        assert len(pairs) == len(set(pairs))

    def test_statistics_populated(self, nyc_records):
        """Statistics should be populated after blocking."""
        blocker = SortedNeighborhoodBlocker(blocking_keys=["borough"], window_size=3)
        blocker.create_candidate_pairs(nyc_records)
        stats = blocker.get_statistics()
        assert stats is not None
        assert stats.total_records == len(nyc_records)

    def test_empty_records(self):
        """Empty input should produce no pairs."""
        blocker = SortedNeighborhoodBlocker(blocking_keys=["borough"])
        pairs = blocker.create_candidate_pairs([])
        assert pairs == []

# ---------------------------------------------------------------------------
# SuffixArrayBlocker tests
# ---------------------------------------------------------------------------

class TestSuffixArrayBlocker:
    """Tests for SuffixArrayBlocker token-based algorithm."""

    def test_token_length_enforced_minimum(self):
        """Token length below 1 should be clamped to 1."""
        blocker = SuffixArrayBlocker(blocking_keys=["address"], token_length=0)
        assert blocker.token_length == 1

    def test_min_tokens_enforced_minimum(self):
        """min_tokens below 1 should be clamped to 1."""
        blocker = SuffixArrayBlocker(blocking_keys=["address"], min_tokens=0)
        assert blocker.min_tokens == 1

    def test_records_sharing_token_are_paired(self):
        """Records that share a token prefix should be candidate pairs."""
        records = [
            {"id": "1", "address": "broadway avenue"},
            {"id": "2", "address": "broadway street"},
            {"id": "3", "address": "atlantic avenue"},
        ]
        blocker = SuffixArrayBlocker(blocking_keys=["address"], token_length=3)
        pairs = blocker.create_candidate_pairs(records)
        assert (0, 1) in pairs

    def test_records_without_shared_tokens_not_paired(self):
        """Records with entirely different tokens should not be paired."""
        records = [
            {"id": "1", "address": "xyz street"},
            {"id": "2", "address": "abc avenue"},
        ]
        blocker = SuffixArrayBlocker(blocking_keys=["address"], token_length=5)
        pairs = blocker.create_candidate_pairs(records)
        assert pairs == []

    def test_no_duplicate_pairs(self, nyc_records):
        """Suffix array blocking should produce no duplicate pairs."""
        blocker = SuffixArrayBlocker(blocking_keys=["address"], token_length=3)
        pairs = blocker.create_candidate_pairs(nyc_records)
        assert len(pairs) == len(set(pairs))

    def test_statistics_populated(self, nyc_records):
        """Statistics should be populated after blocking."""
        blocker = SuffixArrayBlocker(blocking_keys=["address"], token_length=3)
        blocker.create_candidate_pairs(nyc_records)
        stats = blocker.get_statistics()
        assert stats is not None
        assert stats.total_records == len(nyc_records)

    def test_empty_field_value_produces_no_tokens(self):
        """Records with empty blocking field values should not produce tokens."""
        records = [
            {"id": "1", "address": ""},
            {"id": "2", "address": ""},
        ]
        blocker = SuffixArrayBlocker(blocking_keys=["address"], token_length=3)
        pairs = blocker.create_candidate_pairs(records)
        assert pairs == []

    def test_empty_records(self):
        """Empty input should produce no pairs."""
        blocker = SuffixArrayBlocker(blocking_keys=["address"])
        pairs = blocker.create_candidate_pairs([])
        assert pairs == []

# ---------------------------------------------------------------------------
# CanopyBlocker tests
# ---------------------------------------------------------------------------

class TestCanopyBlocker:
    """Tests for CanopyBlocker approximate clustering algorithm."""

    def test_identical_records_are_paired(self):
        """Identical records should always appear in the same canopy."""
        records = [
            {"id": "1", "borough": "MN"},
            {"id": "2", "borough": "MN"},
        ]
        blocker = CanopyBlocker(
            blocking_keys=["borough"],
            loose_threshold=0.5,
            tight_threshold=0.8,
        )
        pairs = blocker.create_candidate_pairs(records)
        assert (0, 1) in pairs

    def test_completely_different_records(self):
        """Records with no common key values should not share a canopy."""
        records = [
            {"id": "1", "borough": "MN", "block": "1001"},
            {"id": "2", "borough": "BK", "block": "2001"},
        ]
        blocker = CanopyBlocker(
            blocking_keys=["borough", "block"],
            loose_threshold=0.9,
            tight_threshold=0.99,
        )
        pairs = blocker.create_candidate_pairs(records)
        assert (0, 1) not in pairs

    def test_statistics_populated(self, nyc_records):
        """Statistics should be populated after blocking."""
        blocker = CanopyBlocker(blocking_keys=["borough"], loose_threshold=0.3, tight_threshold=0.6)
        blocker.create_candidate_pairs(nyc_records)
        stats = blocker.get_statistics()
        assert stats is not None
        assert stats.total_records == len(nyc_records)

    def test_empty_records(self):
        """Empty input should produce no pairs."""
        blocker = CanopyBlocker(blocking_keys=["borough"])
        pairs = blocker.create_candidate_pairs([])
        assert pairs == []

    def test_no_duplicate_pairs(self, nyc_records):
        """CanopyBlocker should produce no duplicate pairs."""
        blocker = CanopyBlocker(blocking_keys=["borough"], loose_threshold=0.3)
        pairs = blocker.create_candidate_pairs(nyc_records)
        assert len(pairs) == len(set(pairs))

    def test_single_record_returns_empty_pairs(self):
        """A single record should yield no candidate pairs."""
        blocker = CanopyBlocker(blocking_keys=["borough"])
        pairs = blocker.create_candidate_pairs([{"id": "1", "borough": "MN"}])
        assert pairs == []

# ---------------------------------------------------------------------------
# CanopyBlocker._record_similarity tests
# ---------------------------------------------------------------------------

class TestCanopyBlockerSimilarity:
    """Tests for the internal _record_similarity method."""

    def test_identical_records_score_one(self):
        """Identical records should return a similarity of 1.0."""
        blocker = CanopyBlocker(blocking_keys=["borough", "block_id"])
        r = {"borough": "MN", "block_id": "1001"}
        assert blocker._record_similarity(r, r) == pytest.approx(1.0)

    def test_completely_different_records_score_zero(self):
        """Records sharing no key values should return 0.0."""
        blocker = CanopyBlocker(blocking_keys=["borough"])
        r1 = {"borough": "MN"}
        r2 = {"borough": "BK"}
        assert blocker._record_similarity(r1, r2) == pytest.approx(0.0)

    def test_partial_prefix_match_scores_half(self):
        """Records matching on the first 3 chars of a single key get 0.5/key."""
        blocker = CanopyBlocker(blocking_keys=["borough"])
        r1 = {"borough": "Manhattan"}
        r2 = {"borough": "Mantle"}
        sim = blocker._record_similarity(r1, r2)
        assert sim == pytest.approx(0.5)

    def test_no_blocking_keys_returns_zero(self):
        """No blocking keys should yield 0.0 similarity."""
        blocker = CanopyBlocker(blocking_keys=[])
        r1 = {"borough": "MN"}
        r2 = {"borough": "MN"}
        assert blocker._record_similarity(r1, r2) == pytest.approx(0.0)

    def test_empty_values_score_zero(self):
        """Records with empty values for all blocking keys should score 0.0."""
        blocker = CanopyBlocker(blocking_keys=["borough"])
        r1 = {"borough": ""}
        r2 = {"borough": ""}
        assert blocker._record_similarity(r1, r2) == pytest.approx(0.0)

# ---------------------------------------------------------------------------
# HybridBlocker tests
# ---------------------------------------------------------------------------

class TestHybridBlocker:
    """Tests for HybridBlocker combining multiple strategies."""

    def test_hybrid_unions_pairs_from_all_blockers(self, nyc_records):
        """HybridBlocker should include all pairs from its sub-blockers."""
        b1 = StandardBlocker(blocking_keys=["borough"])
        b2 = StandardBlocker(blocking_keys=["block_id"])
        hybrid = HybridBlocker(blockers=[b1, b2])

        pairs_b1 = set(b1.create_candidate_pairs(nyc_records))
        pairs_b2 = set(b2.create_candidate_pairs(nyc_records))
        hybrid_pairs = set(hybrid.create_candidate_pairs(nyc_records))

        assert pairs_b1.issubset(hybrid_pairs)
        assert pairs_b2.issubset(hybrid_pairs)

    def test_hybrid_no_duplicate_pairs(self, nyc_records):
        """Hybrid results should contain no duplicate pairs."""
        b1 = StandardBlocker(blocking_keys=["borough"])
        b2 = SortedNeighborhoodBlocker(blocking_keys=["borough"], window_size=2)
        hybrid = HybridBlocker(blockers=[b1, b2])
        pairs = hybrid.create_candidate_pairs(nyc_records)
        assert len(pairs) == len(set(pairs))

    def test_hybrid_statistics_populated(self, nyc_records):
        """Statistics should be set after blocking."""
        b1 = StandardBlocker(blocking_keys=["borough"])
        hybrid = HybridBlocker(blockers=[b1])
        hybrid.create_candidate_pairs(nyc_records)
        stats = hybrid.get_statistics()
        assert stats is not None
        assert stats.total_records == len(nyc_records)

    def test_hybrid_collects_all_unique_keys(self):
        """HybridBlocker should aggregate blocking_keys from all sub-blockers."""
        b1 = StandardBlocker(blocking_keys=["borough"])
        b2 = StandardBlocker(blocking_keys=["block_id"])
        hybrid = HybridBlocker(blockers=[b1, b2])
        assert set(hybrid.blocking_keys) == {"borough", "block_id"}

    def test_hybrid_empty_records(self):
        """Empty input should yield no pairs even with multiple sub-blockers."""
        b1 = StandardBlocker(blocking_keys=["borough"])
        b2 = SortedNeighborhoodBlocker(blocking_keys=["borough"])
        hybrid = HybridBlocker(blockers=[b1, b2])
        assert hybrid.create_candidate_pairs([]) == []

    def test_hybrid_pairs_sorted(self, nyc_records):
        """HybridBlocker should return pairs in sorted order."""
        b1 = StandardBlocker(blocking_keys=["borough"])
        hybrid = HybridBlocker(blockers=[b1])
        pairs = hybrid.create_candidate_pairs(nyc_records)
        assert pairs == sorted(pairs)

# ---------------------------------------------------------------------------
# BlockingAlgorithm._calculate_statistics tests
# ---------------------------------------------------------------------------

class TestCalculateStatistics:
    """Tests for the base _calculate_statistics helper."""

    def test_reduction_ratio_with_one_pair(self):
        """Single pair from n=3 records: (3 - 1) / 3 = 0.667 reduction."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        blocks = {"MN": [0, 1], "BK": [2]}
        stats = blocker._calculate_statistics(
            total_records=3,
            candidate_pairs=1,
            blocks=blocks,
        )
        assert stats.reduction_ratio == pytest.approx(1.0 - 1 / 3, abs=0.01)

    def test_reduction_ratio_zero_possible_pairs(self):
        """With 0 or 1 record there are no possible pairs, ratio should be 0."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        stats = blocker._calculate_statistics(
            total_records=1,
            candidate_pairs=0,
            blocks={"MN": [0]},
        )
        assert stats.reduction_ratio == pytest.approx(0.0)

    def test_largest_block_size(self):
        """Largest block size should reflect the biggest block."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        blocks = {"MN": [0, 1, 2], "BK": [3, 4]}
        stats = blocker._calculate_statistics(5, 4, blocks)
        assert stats.largest_block_size == 3

    def test_empty_blocks_count(self):
        """Empty blocks count should reflect blocks with zero members."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        blocks = {"MN": [0, 1], "BK": [], "QN": [2]}
        stats = blocker._calculate_statistics(3, 1, blocks)
        assert stats.empty_blocks == 1

    def test_blocks_created_count(self):
        """blocks_created should equal the number of keys in the blocks dict."""
        blocker = StandardBlocker(blocking_keys=["borough"])
        blocks = {"MN": [0], "BK": [1], "QN": [2]}
        stats = blocker._calculate_statistics(3, 0, blocks)
        assert stats.blocks_created == 3
