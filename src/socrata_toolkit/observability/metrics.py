"""In-memory metrics collection (counters, gauges, histograms, summaries).

Provides a lightweight, dependency-free metrics layer with Prometheus, JSON and
CSV export. Designed for the toolkit's observability subsystem rather than as a
full Prometheus client.
"""

from __future__ import annotations

import csv
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class HistogramData:
    """Accumulated samples for a histogram or summary metric."""

    count: int = 0
    total: float = 0.0
    samples: list[float] = field(default_factory=list)

    def observe(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.samples.append(value)

    @property
    def mean(self) -> float:
        return self.total / self.count if self.count else 0.0

    def quantile(self, q: float) -> float:
        """Return the q-quantile (0..1) using nearest-rank on sorted samples."""
        if not self.samples:
            return 0.0
        ordered = sorted(self.samples)
        if q <= 0:
            return ordered[0]
        if q >= 1:
            return ordered[-1]
        rank = math.ceil(q * len(ordered)) - 1
        rank = max(0, min(rank, len(ordered) - 1))
        return ordered[rank]


class MetricsCollector:
    """Collects counter, gauge, histogram and summary metrics in memory."""

    def __init__(self) -> None:
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, HistogramData] = {}
        self._summaries: dict[str, HistogramData] = {}

    # -- recording ------------------------------------------------------
    def increment(self, name: str, value: float = 1.0) -> None:
        self._counters[name] = self._counters.get(name, 0.0) + value

    def set_gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def observe_histogram(self, name: str, value: float) -> None:
        self._histograms.setdefault(name, HistogramData()).observe(value)

    def observe_summary(self, name: str, value: float) -> None:
        self._summaries.setdefault(name, HistogramData()).observe(value)

    # -- accessors ------------------------------------------------------
    @property
    def counter_count(self) -> int:
        return len(self._counters)

    @property
    def gauge_count(self) -> int:
        return len(self._gauges)

    @property
    def histogram_count(self) -> int:
        return len(self._histograms)

    @property
    def summary_count(self) -> int:
        return len(self._summaries)

    def summary_dict(self) -> dict[str, Any]:
        return {
            "counter_count": self.counter_count,
            "gauge_count": self.gauge_count,
            "histogram_count": self.histogram_count,
            "summary_count": self.summary_count,
            "timestamp": time.time(),
        }

    # -- export ---------------------------------------------------------
    def export_json(self) -> str:
        payload = {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                name: {"count": h.count, "sum": h.total, "mean": h.mean,
                       "p50": h.quantile(0.5), "p95": h.quantile(0.95), "p99": h.quantile(0.99)}
                for name, h in self._histograms.items()
            },
            "summaries": {
                name: {"count": s.count, "sum": s.total, "mean": s.mean}
                for name, s in self._summaries.items()
            },
        }
        return json.dumps(payload, indent=2)

    def export_prometheus(self) -> str:
        lines: list[str] = []
        for name, value in sorted(self._counters.items()):
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for name, value in sorted(self._gauges.items()):
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        for name, h in sorted(self._histograms.items()):
            lines.append(f"# TYPE {name} histogram")
            lines.append(f"{name}_count {h.count}")
            lines.append(f"{name}_sum {h.total}")
        for name, s in sorted(self._summaries.items()):
            lines.append(f"# TYPE {name} summary")
            lines.append(f"{name}_count {s.count}")
            lines.append(f"{name}_sum {s.total}")
        return "\n".join(lines) + ("\n" if lines else "")

    def export_csv(self, path: str | Path) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["metric_type", "name", "value"])
            for name, value in self._counters.items():
                writer.writerow(["counter", name, value])
            for name, value in self._gauges.items():
                writer.writerow(["gauge", name, value])
            for name, h in self._histograms.items():
                writer.writerow(["histogram", name, h.total])
            for name, s in self._summaries.items():
                writer.writerow(["summary", name, s.total])

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._summaries.clear()
