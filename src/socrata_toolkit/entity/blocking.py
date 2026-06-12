"""
Blocking algorithms for scalable entity resolution.

Provides efficient candidate pair generation for large datasets,
reducing complexity from O(n²) to near-linear for practical datasets.

Strategies:
- Standard Blocking: Single key blocks candidates
- Sorted Neighborhood: Sort by key, compare neighbors
- Suffix Arrays: Prefix matching for fuzzy fields
- Canopy Clustering: Fast approximate clustering

Example:
    >>> from socrata_toolkit.entity.blocking import StandardBlocker
    >>> blocker = StandardBlocker(blocking_keys=['borough', 'block_id'])
    >>> pairs = blocker.create_candidate_pairs(records)
    >>> len(pairs)  # Much less than n*(n-1)/2
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class BlockStatistics:
    """Statistics about blocking results."""
    total_records: int
    total_possible_pairs: int
    candidate_pairs: int
    reduction_ratio: float
    largest_block_size: int
    blocks_created: int
    empty_blocks: int

class BlockingAlgorithm(ABC):
    """Base class for blocking algorithms."""

    def __init__(self, blocking_keys: list[str]):
        """
        Initialize blocker.

        Args:
            blocking_keys: Fields to use for blocking
        """
        self.blocking_keys = blocking_keys
        self._statistics: BlockStatistics | None = None

    @abstractmethod
    def create_candidate_pairs(
        self,
        records: list[dict[str, Any]]
    ) -> list[tuple[int, int]]:
        """
        Create candidate record pairs for matching.

        Args:
            records: List of records

        Returns:
            List of (record_index1, record_index2) pairs
        """
        pass

    def get_statistics(self) -> BlockStatistics | None:
        """Get statistics from last blocking operation."""
        return self._statistics

    def _calculate_statistics(
        self,
        total_records: int,
        candidate_pairs: int,
        blocks: dict[str, list[int]]
    ) -> BlockStatistics:
        """Calculate blocking statistics."""
        total_possible = total_records * (total_records - 1) // 2
        reduction_ratio = 1.0 - (candidate_pairs / total_possible) if total_possible > 0 else 0.0
        largest_block = max((len(v) for v in blocks.values()), default=0)
        empty_blocks = sum(1 for v in blocks.values() if len(v) == 0)

        return BlockStatistics(
            total_records=total_records,
            total_possible_pairs=total_possible,
            candidate_pairs=candidate_pairs,
            reduction_ratio=reduction_ratio,
            largest_block_size=largest_block,
            blocks_created=len(blocks),
            empty_blocks=empty_blocks
        )

class StandardBlocker(BlockingAlgorithm):
    """
    Standard blocking algorithm.

    Groups records by blocking key values, creates pairs within groups.
    Simple but effective for moderately sized datasets.
    """

    def create_candidate_pairs(
        self,
        records: list[dict[str, Any]]
    ) -> list[tuple[int, int]]:
        """
        Create candidate pairs using standard blocking.

        Args:
            records: List of records

        Returns:
            List of (index1, index2) pairs
        """
        # Create blocks
        blocks = self._create_blocks(records)

        # Generate pairs within blocks
        pairs = []
        for indices in blocks.values():
            # Compare all pairs within block
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    pairs.append((indices[i], indices[j]))

        # Calculate statistics
        self._statistics = self._calculate_statistics(
            len(records),
            len(pairs),
            blocks
        )

        return pairs

    def _create_blocks(self, records: list[dict[str, Any]]) -> dict[str, list[int]]:
        """Create blocks from records using blocking keys."""
        blocks: dict[str, list[int]] = {}

        for idx, record in enumerate(records):
            block_key = self._generate_block_key(record)

            if block_key not in blocks:
                blocks[block_key] = []
            blocks[block_key].append(idx)

        return blocks

    def _generate_block_key(self, record: dict[str, Any]) -> str:
        """Generate blocking key from record."""
        key_parts = []

        for field in self.blocking_keys:
            value = record.get(field, '')
            if value:
                # Normalize value
                value_str = str(value).strip().lower()
                key_parts.append(value_str)

        return '|'.join(key_parts) if key_parts else '__none__'

class SortedNeighborhoodBlocker(BlockingAlgorithm):
    """
    Sorted neighborhood blocking.

    Sorts records by blocking key, compares neighbors within window.
    Good for handling typos in blocking keys.
    """

    def __init__(
        self,
        blocking_keys: list[str],
        window_size: int = 50
    ):
        """
        Initialize sorted neighborhood blocker.

        Args:
            blocking_keys: Fields for sorting
            window_size: Size of comparison window
        """
        super().__init__(blocking_keys)
        self.window_size = max(2, window_size)

    def create_candidate_pairs(
        self,
        records: list[dict[str, Any]]
    ) -> list[tuple[int, int]]:
        """
        Create candidate pairs using sorted neighborhood.

        Args:
            records: List of records

        Returns:
            List of (index1, index2) pairs
        """
        # Create sortable key for each record
        sortable_records = [
            (self._generate_sort_key(r), i, r)
            for i, r in enumerate(records)
        ]

        # Sort by key
        sortable_records.sort(key=lambda x: x[0])

        # Create pairs within windows
        pairs = set()
        for i in range(len(sortable_records)):
            # Look ahead in window
            for j in range(i + 1, min(i + self.window_size, len(sortable_records))):
                idx1 = sortable_records[i][1]
                idx2 = sortable_records[j][1]

                # Avoid duplicate pairs
                if idx1 < idx2:
                    pairs.add((idx1, idx2))
                else:
                    pairs.add((idx2, idx1))

        pairs_list = list(pairs)

        # Calculate statistics
        blocks = self._create_pseudo_blocks(sortable_records)
        self._statistics = self._calculate_statistics(
            len(records),
            len(pairs_list),
            blocks
        )

        return pairs_list

    def _generate_sort_key(self, record: dict[str, Any]) -> str:
        """Generate sortable key from record."""
        key_parts = []

        for field in self.blocking_keys:
            value = record.get(field, '')
            if value:
                value_str = str(value).strip().lower()
                key_parts.append(value_str)

        return '|'.join(key_parts) if key_parts else '__none__'

    def _create_pseudo_blocks(
        self,
        sortable_records: list[tuple[str, int, dict]]
    ) -> dict[str, list[int]]:
        """Create pseudo-blocks for statistics."""
        blocks: dict[str, list[int]] = {}

        for sort_key, idx, _ in sortable_records:
            if sort_key not in blocks:
                blocks[sort_key] = []
            blocks[sort_key].append(idx)

        return blocks

class SuffixArrayBlocker(BlockingAlgorithm):
    """
    Suffix array blocking for fuzzy matching.

    Uses token/suffix-based blocking for fields with typos.
    """

    def __init__(
        self,
        blocking_keys: list[str],
        token_length: int = 3,
        min_tokens: int = 1
    ):
        """
        Initialize suffix array blocker.

        Args:
            blocking_keys: Fields for tokenization
            token_length: Length of tokens to extract
            min_tokens: Minimum tokens to create block
        """
        super().__init__(blocking_keys)
        self.token_length = max(1, token_length)
        self.min_tokens = max(1, min_tokens)

    def create_candidate_pairs(
        self,
        records: list[dict[str, Any]]
    ) -> list[tuple[int, int]]:
        """
        Create candidate pairs using suffix arrays.

        Args:
            records: List of records

        Returns:
            List of (index1, index2) pairs
        """
        # Extract tokens for each record
        record_tokens: list[set[str]] = []
        for record in records:
            tokens = self._extract_tokens(record)
            record_tokens.append(tokens)

        # Create inverted index: token -> record indices
        token_index: dict[str, set[int]] = {}
        for idx, tokens in enumerate(record_tokens):
            for token in tokens:
                if token not in token_index:
                    token_index[token] = set()
                token_index[token].add(idx)

        # Generate candidate pairs from shared tokens
        pairs: set[tuple[int, int]] = set()
        for indices in token_index.values():
            if len(indices) > 1:
                # Create pairs of records sharing this token
                indices_list = sorted(list(indices))
                for i in range(len(indices_list)):
                    for j in range(i + 1, len(indices_list)):
                        idx1, idx2 = indices_list[i], indices_list[j]
                        if idx1 < idx2:
                            pairs.add((idx1, idx2))
                        else:
                            pairs.add((idx2, idx1))

        pairs_list = list(pairs)

        # Create pseudo-blocks for statistics
        blocks = {
            token: list(indices)
            for token, indices in token_index.items()
        }

        self._statistics = self._calculate_statistics(
            len(records),
            len(pairs_list),
            blocks
        )

        return pairs_list

    def _extract_tokens(self, record: dict[str, Any]) -> set[str]:
        """Extract tokens from record."""
        tokens: set[str] = set()

        for field in self.blocking_keys:
            value = record.get(field, '')
            if not value:
                continue

            value_str = str(value).strip().lower()

            # Extract word tokens
            words = value_str.split()
            for word in words:
                if len(word) >= self.token_length:
                    tokens.add(word[:self.token_length])

        return tokens

class CanopyBlocker(BlockingAlgorithm):
    """
    Canopy clustering for fast approximate blocking.

    Uses quick approximate clustering to create blocks,
    useful for very large datasets where O(n log n) is needed.
    """

    def __init__(
        self,
        blocking_keys: list[str],
        loose_threshold: float = 0.5,
        tight_threshold: float = 0.8
    ):
        """
        Initialize canopy blocker.

        Args:
            blocking_keys: Fields for clustering
            loose_threshold: Loose canopy threshold (add to block)
            tight_threshold: Tight canopy threshold (start new canopy)
        """
        super().__init__(blocking_keys)
        self.loose_threshold = loose_threshold
        self.tight_threshold = tight_threshold

    def create_candidate_pairs(
        self,
        records: list[dict[str, Any]]
    ) -> list[tuple[int, int]]:
        """
        Create candidate pairs using canopy clustering.

        Args:
            records: List of records

        Returns:
            List of (index1, index2) pairs
        """
        # Create canopies
        canopies = self._create_canopies(records)

        # Generate pairs within canopies
        pairs: set[tuple[int, int]] = set()
        for canopy in canopies:
            # Create all pairs within canopy
            for i in range(len(canopy)):
                for j in range(i + 1, len(canopy)):
                    idx1, idx2 = canopy[i], canopy[j]
                    if idx1 < idx2:
                        pairs.add((idx1, idx2))
                    else:
                        pairs.add((idx2, idx1))

        pairs_list = list(pairs)

        # Create pseudo-blocks for statistics
        blocks = {
            f'canopy_{i}': list(canopy)
            for i, canopy in enumerate(canopies)
        }

        self._statistics = self._calculate_statistics(
            len(records),
            len(pairs_list),
            blocks
        )

        return pairs_list

    def _create_canopies(
        self,
        records: list[dict[str, Any]]
    ) -> list[list[int]]:
        """Create canopies from records."""
        canopies: list[list[int]] = []
        remaining = set(range(len(records)))

        while remaining:
            # Start new canopy with random remaining record
            canopy_seed = remaining.pop()
            canopy = [canopy_seed]

            # Find records close to seed (loose threshold)
            for idx in list(remaining):
                similarity = self._record_similarity(
                    records[canopy_seed],
                    records[idx]
                )

                if similarity >= self.loose_threshold:
                    canopy.append(idx)

                    # If very close (tight threshold), remove from pool
                    if similarity >= self.tight_threshold:
                        remaining.discard(idx)

            canopies.append(canopy)

        return canopies

    def _record_similarity(
        self,
        record1: dict[str, Any],
        record2: dict[str, Any]
    ) -> float:
        """Calculate quick similarity between records."""
        if not self.blocking_keys:
            return 0.0

        matches = 0
        for field in self.blocking_keys:
            val1 = str(record1.get(field, '')).lower().strip()
            val2 = str(record2.get(field, '')).lower().strip()

            if val1 and val2:
                if val1 == val2:
                    matches += 1
                # Partial match on first 3 chars
                elif val1[:3] == val2[:3]:
                    matches += 0.5

        return matches / len(self.blocking_keys)

class HybridBlocker(BlockingAlgorithm):
    """
    Hybrid blocking using multiple strategies.

    Combines multiple blocking algorithms to maximize recall
    while managing computational cost.
    """

    def __init__(
        self,
        blockers: list[BlockingAlgorithm]
    ):
        """
        Initialize hybrid blocker.

        Args:
            blockers: List of blocking algorithms to combine
        """
        # Collect all unique blocking keys
        all_keys = set()
        for blocker in blockers:
            all_keys.update(blocker.blocking_keys)

        super().__init__(list(all_keys))
        self.blockers = blockers

    def create_candidate_pairs(
        self,
        records: list[dict[str, Any]]
    ) -> list[tuple[int, int]]:
        """
        Create candidate pairs by combining multiple blockers.

        Args:
            records: List of records

        Returns:
            List of (index1, index2) pairs (union of all blockers)
        """
        all_pairs: set[tuple[int, int]] = set()

        for blocker in self.blockers:
            pairs = blocker.create_candidate_pairs(records)
            all_pairs.update(pairs)

        pairs_list = sorted(list(all_pairs))

        # Calculate combined statistics
        combined_blocks: dict[str, list[int]] = {}
        total_possible = len(records) * (len(records) - 1) // 2

        self._statistics = BlockStatistics(
            total_records=len(records),
            total_possible_pairs=total_possible,
            candidate_pairs=len(pairs_list),
            reduction_ratio=1.0 - (len(pairs_list) / total_possible) if total_possible > 0 else 0.0,
            largest_block_size=len(records),
            blocks_created=len(self.blockers),
            empty_blocks=0
        )

        return pairs_list
