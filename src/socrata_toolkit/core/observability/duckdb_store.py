import duckdb
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

class DuckDBObservabilityStore:
    """
    Persistent observability storage using DuckDB.
    Tracks routing decisions, feedback, and weight history.
    """

    def __init__(self, db_path: str = "data/local_db/router_observability.duckdb"):
        """
        Initialize DuckDB store.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._initialize_schema()

    def _initialize_schema(self):
        """Create observability tables if they don't exist"""
        # Routing decisions table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS routing_decisions (
                id VARCHAR PRIMARY KEY,
                question VARCHAR,
                matched_kpi_id VARCHAR,
                confidence FLOAT,
                ensemble_status VARCHAR,
                latency_ms INTEGER,
                router_source VARCHAR,
                created_at TIMESTAMP
            )
        """)

        # Routing feedback table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS routing_feedback (
                id VARCHAR PRIMARY KEY,
                routing_decision_id VARCHAR,
                analyst_marked_helpful BOOLEAN,
                corrected_kpi_id VARCHAR,
                feedback_text VARCHAR,
                created_at TIMESTAMP,
                FOREIGN KEY (routing_decision_id) REFERENCES routing_decisions(id)
            )
        """)

        # Weight history table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS weight_history (
                id VARCHAR PRIMARY KEY,
                timestamp TIMESTAMP,
                strategy VARCHAR,
                weight FLOAT,
                source VARCHAR,
                feedback_count INTEGER
            )
        """)

    def record_routing_decision(
        self,
        decision_id: str,
        question: str,
        matched_kpi_id: Optional[str],
        confidence: float,
        ensemble_status: str,
        latency_ms: int,
        router_source: str
    ) -> None:
        """Record a routing decision"""
        self.conn.execute("""
            INSERT INTO routing_decisions
            (id, question, matched_kpi_id, confidence, ensemble_status, latency_ms, router_source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            decision_id,
            question,
            matched_kpi_id,
            confidence,
            ensemble_status,
            latency_ms,
            router_source,
            datetime.utcnow().isoformat()
        ])

    def record_feedback(
        self,
        feedback_id: str,
        routing_decision_id: str,
        helpful: bool,
        corrected_kpi_id: Optional[str] = None,
        feedback_text: Optional[str] = None
    ) -> None:
        """Record analyst feedback on a routing decision"""
        self.conn.execute("""
            INSERT INTO routing_feedback
            (id, routing_decision_id, analyst_marked_helpful, corrected_kpi_id, feedback_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            feedback_id,
            routing_decision_id,
            helpful,
            corrected_kpi_id,
            feedback_text,
            datetime.utcnow().isoformat()
        ])

    def record_weight_update(
        self,
        weight_id: str,
        strategy: str,
        weight: float,
        source: str,
        feedback_count: int
    ) -> None:
        """Record a weight update event"""
        self.conn.execute("""
            INSERT INTO weight_history
            (id, timestamp, strategy, weight, source, feedback_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            weight_id,
            datetime.utcnow().isoformat(),
            strategy,
            weight,
            source,
            feedback_count
        ])

    def get_routing_accuracy(self, window_hours: int = 24) -> float:
        """
        Get routing accuracy over a time window.
        Accuracy = helpful / (helpful + wrong)
        """
        result = self.conn.execute(f"""
            SELECT
                SUM(CASE WHEN analyst_marked_helpful THEN 1 ELSE 0 END) as helpful,
                SUM(CASE WHEN NOT analyst_marked_helpful THEN 1 ELSE 0 END) as wrong
            FROM routing_feedback
            WHERE created_at > now() - interval '{window_hours} hours'
        """).fetchall()

        if not result or result[0][0] is None:
            return 0.0

        helpful, wrong = result[0]
        total = (helpful or 0) + (wrong or 0)
        return helpful / total if total > 0 else 0.0

    def get_recent_feedback(self, limit: int = 100) -> List[Dict]:
        """Get recent feedback records"""
        results = self.conn.execute(f"""
            SELECT
                rf.id, rf.routing_decision_id, rf.analyst_marked_helpful,
                rf.corrected_kpi_id, rd.matched_kpi_id, rd.question, rd.created_at
            FROM routing_feedback rf
            JOIN routing_decisions rd ON rf.routing_decision_id = rd.id
            ORDER BY rf.created_at DESC
            LIMIT {limit}
        """).fetchall()

        return [
            {
                'feedback_id': r[0],
                'routing_decision_id': r[1],
                'helpful': r[2],
                'corrected_kpi_id': r[3],
                'original_kpi_id': r[4],
                'question': r[5],
                'timestamp': r[6]
            }
            for r in results
        ]

    def close(self):
        """Close database connection"""
        self.conn.close()


__all__ = ["DuckDBObservabilityStore"]
