import pytest
import tempfile
import uuid
from pathlib import Path
from socrata_toolkit.core.observability.duckdb_store import DuckDBObservabilityStore


def test_duckdb_store_initialize():
    """Test DuckDB store initialization"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test.duckdb"
        store = DuckDBObservabilityStore(db_path)

        # Verify tables exist
        tables = store.conn.execute(
            "SELECT table_name FROM information_schema.tables"
        ).fetchall()
        table_names = [t[0] for t in tables]

        assert "routing_decisions" in table_names
        assert "routing_feedback" in table_names
        assert "weight_history" in table_names

        store.close()


def test_record_routing_decision():
    """Test recording routing decisions"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test.duckdb"
        store = DuckDBObservabilityStore(db_path)

        decision_id = str(uuid.uuid4())
        store.record_routing_decision(
            decision_id=decision_id,
            question="test question",
            matched_kpi_id="KPI-089",
            confidence=0.85,
            ensemble_status="HIGH_CONFIDENCE",
            latency_ms=100,
            router_source="hybrid"
        )

        # Verify record exists
        result = store.conn.execute(
            "SELECT matched_kpi_id, confidence FROM routing_decisions WHERE id = ?",
            [decision_id]
        ).fetchall()

        assert len(result) == 1
        assert result[0][0] == "KPI-089"
        assert abs(result[0][1] - 0.85) < 0.001

        store.close()


def test_record_feedback():
    """Test recording feedback"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test.duckdb"
        store = DuckDBObservabilityStore(db_path)

        # First record a decision
        decision_id = str(uuid.uuid4())
        store.record_routing_decision(
            decision_id=decision_id,
            question="test",
            matched_kpi_id="KPI-089",
            confidence=0.8,
            ensemble_status="success",
            latency_ms=100,
            router_source="hybrid"
        )

        # Record feedback
        feedback_id = str(uuid.uuid4())
        store.record_feedback(
            feedback_id=feedback_id,
            routing_decision_id=decision_id,
            helpful=True,
            corrected_kpi_id=None,
            feedback_text="Good match"
        )

        # Verify
        result = store.conn.execute(
            "SELECT analyst_marked_helpful FROM routing_feedback WHERE id = ?",
            [feedback_id]
        ).fetchall()

        assert len(result) == 1
        assert result[0][0] == True

        store.close()


def test_get_routing_accuracy():
    """Test accuracy calculation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test.duckdb"
        store = DuckDBObservabilityStore(db_path)

        # Record decisions and feedback
        for i in range(10):
            decision_id = str(uuid.uuid4())
            store.record_routing_decision(
                decision_id=decision_id,
                question=f"q{i}",
                matched_kpi_id="KPI-089",
                confidence=0.8,
                ensemble_status="success",
                latency_ms=100,
                router_source="hybrid"
            )

            # 8 helpful, 2 wrong
            helpful = i < 8
            store.record_feedback(
                feedback_id=str(uuid.uuid4()),
                routing_decision_id=decision_id,
                helpful=helpful,
                corrected_kpi_id=None
            )

        accuracy = store.get_routing_accuracy(window_hours=24)
        assert accuracy == 0.8

        store.close()
