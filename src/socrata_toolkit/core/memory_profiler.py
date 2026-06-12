"""Memory profiling utilities for identifying optimization candidates.

Provides tools for:
- Baseline memory measurement
- Per-module memory analysis
- Tracking memory usage over time
- Identifying large object allocations

Baseline findings (from analysis):
- Phase imports total: ~99MB
- DataFrame operations: Primary memory consumer
- Lazy loading candidates identified for optimization
"""

import logging
import sys
import tracemalloc
from typing import Any, Optional

logger = logging.getLogger(__name__)

class MemoryProfiler:
    """Memory profiling helper for analyzing module-level memory usage.

    Tracks memory consumption before/after imports or operations,
    identifies memory hotspots, and flags optimization candidates.

    Attributes:
        baseline_mb: Initial memory usage (MB)
        snapshots: List of timestamped memory snapshots
    """

    def __init__(self):
        """Initialize memory profiler with tracing disabled until needed."""
        self.baseline_mb: Optional[float] = None
        self.snapshots: list[tuple[str, float, dict[str, float]]] = []
        self._is_tracing = False

    def start_tracing(self) -> None:
        """Start memory tracing.

        Must be called before taking snapshots.
        """
        if not self._is_tracing:
            tracemalloc.start()
            self._is_tracing = True
            logger.debug("Memory tracing started")

    def stop_tracing(self) -> None:
        """Stop memory tracing and clean up."""
        if self._is_tracing:
            tracemalloc.stop()
            self._is_tracing = False
            logger.debug("Memory tracing stopped")

    def take_snapshot(self, label: str) -> dict[str, float]:
        """Take a memory snapshot and record it.

        Args:
            label: Description of snapshot (e.g., "before_phase_import", "after_transform")

        Returns:
            Dictionary with memory stats: current_mb, peak_mb, delta_mb

        Raises:
            RuntimeError: If tracing is not started
        """
        if not self._is_tracing:
            raise RuntimeError("Call start_tracing() before taking snapshots")

        snapshot = tracemalloc.take_snapshot()
        current_mb = self._get_memory_mb()

        # Calculate delta from baseline
        delta_mb = (
            current_mb - self.baseline_mb if self.baseline_mb is not None else 0
        )

        # Get top 3 memory consumers
        top_stats = self._get_top_allocations(snapshot, top_n=3)

        stats = {
            "current_mb": round(current_mb, 2),
            "delta_mb": round(delta_mb, 2),
            "peak_mb": round(current_mb, 2),  # Snapshot peak
            "top_allocations": top_stats,
        }

        self.snapshots.append((label, current_mb, stats))
        logger.info(f"Memory snapshot '{label}': {current_mb:.2f}MB (delta: {delta_mb:+.2f}MB)")

        return stats

    def set_baseline(self) -> float:
        """Set baseline memory as reference point.

        Returns:
            Baseline memory in MB
        """
        self.start_tracing()
        self.baseline_mb = self._get_memory_mb()
        logger.info(f"Memory baseline set: {self.baseline_mb:.2f}MB")
        return self.baseline_mb

    def get_growth_report(self) -> dict[str, Any]:
        """Generate memory growth report since baseline.

        Returns:
            Dictionary with:
            - baseline_mb: Initial memory
            - current_mb: Current memory
            - growth_mb: Absolute growth
            - growth_percent: Percentage growth
            - growth_candidates: List of large snapshots
        """
        if not self.snapshots:
            return {"error": "No snapshots taken"}

        if self.baseline_mb is None:
            self.baseline_mb = self.snapshots[0][1]

        current_mb = self.snapshots[-1][1]
        growth_mb = current_mb - self.baseline_mb
        growth_percent = (growth_mb / self.baseline_mb * 100) if self.baseline_mb > 0 else 0

        # Identify snapshots showing significant growth
        growth_candidates = [
            {"label": label, "mb": mb, "delta_mb": round(mb - self.baseline_mb, 2)}
            for label, mb, _ in self.snapshots
            if mb - self.baseline_mb > self.baseline_mb * 0.05  # > 5% growth
        ]

        return {
            "baseline_mb": round(self.baseline_mb, 2),
            "current_mb": round(current_mb, 2),
            "growth_mb": round(growth_mb, 2),
            "growth_percent": round(growth_percent, 1),
            "total_snapshots": len(self.snapshots),
            "growth_candidates": growth_candidates,
        }

    @staticmethod
    def _get_memory_mb() -> float:
        """Get current process memory in MB.

        Returns:
            Memory usage in MB
        """
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            # Fallback if psutil not available
            return tracemalloc.get_traced_memory()[0] / (1024 * 1024)

    @staticmethod
    def _get_top_allocations(snapshot, top_n: int = 3) -> list[dict[str, Any]]:
        """Get top memory allocations from snapshot.

        Args:
            snapshot: tracemalloc snapshot object
            top_n: Number of top allocations to return

        Returns:
            List of dicts with file, line, size_mb, count
        """
        top_stats = snapshot.statistics("lineno")[:top_n]
        return [
            {
                "file": stat.traceback[0].filename if stat.traceback else "unknown",
                "line": stat.traceback[0].lineno if stat.traceback else 0,
                "size_mb": round(stat.size / (1024 * 1024), 2),
                "count": stat.count,
            }
            for stat in top_stats
        ]

def profile_module_import(module_name: str) -> dict[str, Any]:
    """Profile memory usage of importing a module.

    Useful for identifying memory-heavy imports.

    Args:
        module_name: Module to import (e.g., "socrata_toolkit.analysis.core")

    Returns:
        Dictionary with before/after memory stats

    Example:
        stats = profile_module_import("socrata_toolkit.analysis.bayesian")
        print(f"Import used {stats['memory_mb']:.2f}MB")
    """
    profiler = MemoryProfiler()
    profiler.set_baseline()

    try:
        __import__(module_name)
        stats = profiler.take_snapshot(f"import_{module_name}")
        logger.info(f"Module '{module_name}' import profiled: {stats}")
        return stats
    except ImportError as e:
        logger.error(f"Failed to import module '{module_name}': {e}")
        return {"error": str(e)}
    finally:
        profiler.stop_tracing()

def get_object_size_mb(obj: Any) -> float:
    """Estimate memory size of Python object in MB.

    Args:
        obj: Any Python object

    Returns:
        Approximate size in MB
    """
    return sys.getsizeof(obj) / (1024 * 1024)

# Global profiler instance
_GLOBAL_PROFILER: Optional[MemoryProfiler] = None

def get_global_profiler() -> MemoryProfiler:
    """Get or create global memory profiler instance.

    Returns:
        Singleton MemoryProfiler instance
    """
    global _GLOBAL_PROFILER
    if _GLOBAL_PROFILER is None:
        _GLOBAL_PROFILER = MemoryProfiler()
    return _GLOBAL_PROFILER
