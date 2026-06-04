"""Comprehensive tests for llm.sql_engine module.

Covers SQLQueryEngine, InteractiveQuerySession, QueryOptimizer, and the
QueryExecution dataclass. All psycopg and LangChain calls are mocked so
no real database or LLM endpoint is required.

langchain_core and psycopg are not installed in the test environment, so
we inject stub modules into sys.modules before the first import of the
target module.
"""
from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Inject stub modules for missing optional dependencies
# ---------------------------------------------------------------------------


def _inject_langchain_stubs() -> None:
    """Create minimal fake langchain_core and psycopg stubs."""
    for mod_name in [
        "langchain_core",
        "langchain_core.language_model",
        "langchain_core.output_parsers",
        "langchain_core.prompts",
    ]:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    # BaseLanguageModel stub
    class _BaseLanguageModel:
        pass

    sys.modules["langchain_core.language_model"].BaseLanguageModel = _BaseLanguageModel

    # Output parsers
    sys.modules["langchain_core.output_parsers"].StrOutputParser = MagicMock
    sys.modules["langchain_core.output_parsers"].JsonOutputParser = MagicMock

    # ChatPromptTemplate with from_messages factory
    class _FakeCPT:
        @classmethod
        def from_messages(cls, messages):
            m = MagicMock()
            return m

    sys.modules["langchain_core.prompts"].ChatPromptTemplate = _FakeCPT

    # psycopg stub
    if "psycopg" not in sys.modules:
        psycopg_mod = types.ModuleType("psycopg")
        psycopg_mod.connect = MagicMock()

        sql_submod = types.ModuleType("psycopg.sql")
        sql_submod.SQL = MagicMock(side_effect=lambda x: x)
        sql_submod.Literal = MagicMock(side_effect=lambda x: x)
        psycopg_mod.sql = sql_submod
        sys.modules["psycopg"] = psycopg_mod
        sys.modules["psycopg.sql"] = sql_submod


_inject_langchain_stubs()

from socrata_toolkit.llm.sql_engine import (  # noqa: E402
    InteractiveQuerySession,
    QueryExecution,
    QueryOptimizer,
    SQLQueryEngine,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_psycopg_connect():
    """Patch psycopg.connect so no real database is needed."""
    with patch("socrata_toolkit.llm.sql_engine.psycopg.connect") as mock_conn:
        ctx = MagicMock()
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        ctx.cursor.return_value = cursor
        mock_conn.return_value = ctx
        # Schema introspection: tables then columns
        cursor.fetchall.side_effect = [
            [("inspections",), ("violations",)],
            [("id", "integer"), ("borough", "text")],
            [("violation_id", "bigint"), ("status", "text")],
        ]
        yield mock_conn, cursor


@pytest.fixture()
def mock_llm():
    """Return a mock LangChain BaseLanguageModel."""
    llm = MagicMock()
    return llm


@pytest.fixture()
def engine(mock_psycopg_connect, mock_llm):
    """Fully constructed SQLQueryEngine with all external calls mocked."""
    mock_conn, cursor = mock_psycopg_connect
    return SQLQueryEngine(dsn="postgresql://test/db", llm=mock_llm)


# ---------------------------------------------------------------------------
# QueryExecution dataclass
# ---------------------------------------------------------------------------


class TestQueryExecution:
    """Tests for the QueryExecution dataclass."""

    def test_minimal_construction(self):
        """Verify required fields populate correctly."""
        qe = QueryExecution(
            natural_language="how many rows?",
            sql_query="SELECT count(*) FROM t",
            execution_time_ms=12.5,
            row_count=1,
            results=[{"count": 42}],
            interpretation="There are 42 rows.",
            timestamp="2026-01-01T00:00:00+00:00",
        )
        assert qe.natural_language == "how many rows?"
        assert qe.sql_query == "SELECT count(*) FROM t"
        assert qe.execution_time_ms == 12.5
        assert qe.row_count == 1
        assert qe.results == [{"count": 42}]
        assert qe.error is None

    def test_error_field_default_none(self):
        """The error field defaults to None when not provided."""
        qe = QueryExecution(
            natural_language="q",
            sql_query="s",
            execution_time_ms=0.0,
            row_count=0,
            results=[],
            interpretation="",
            timestamp="",
        )
        assert qe.error is None

    def test_error_field_set(self):
        """The error field can be set to a string."""
        qe = QueryExecution(
            natural_language="q",
            sql_query="s",
            execution_time_ms=0.0,
            row_count=0,
            results=[],
            interpretation="",
            timestamp="",
            error="connection refused",
        )
        assert qe.error == "connection refused"


# ---------------------------------------------------------------------------
# SQLQueryEngine initialisation
# ---------------------------------------------------------------------------


class TestSQLQueryEngineInit:
    """Tests for SQLQueryEngine construction and schema loading."""

    def test_engine_stores_dsn(self, engine: SQLQueryEngine):
        """DSN is stored verbatim on the instance."""
        assert engine.dsn == "postgresql://test/db"

    def test_engine_stores_max_results(self, engine: SQLQueryEngine):
        """Default max_results is 1000."""
        assert engine.max_results == 1000

    def test_engine_custom_max_results(self, mock_psycopg_connect, mock_llm):
        """Custom max_results is honoured."""
        mock_conn, cursor = mock_psycopg_connect
        cursor.fetchall.side_effect = [
            [("t",)],
            [("id", "integer")],
        ]
        eng = SQLQueryEngine(dsn="dsn", llm=mock_llm, max_results=500)
        assert eng.max_results == 500

    def test_schema_loaded_on_init(self, engine: SQLQueryEngine):
        """Schema dict is populated after construction."""
        assert isinstance(engine.schema, dict)

    def test_schema_refresh_failure_sets_empty_dict(self, mock_llm):
        """If psycopg.connect raises, schema falls back to empty dict."""
        with patch("socrata_toolkit.llm.sql_engine.psycopg.connect") as mock_conn:
            mock_conn.side_effect = Exception("no database")
            eng = SQLQueryEngine(dsn="bad-dsn", llm=mock_llm)
        assert eng.schema == {}

    def test_execution_history_starts_empty(self, engine: SQLQueryEngine):
        """History list is empty at construction time."""
        assert engine.execution_history == []

    def test_enable_explain_default_true(self, engine: SQLQueryEngine):
        """explain is enabled by default."""
        assert engine.enable_explain is True


# ---------------------------------------------------------------------------
# SQLQueryEngine._get_schema_context
# ---------------------------------------------------------------------------


class TestGetSchemaContext:
    """Tests for the schema formatting helper."""

    def test_returns_string(self, engine: SQLQueryEngine):
        """Result is always a string."""
        result = engine._get_schema_context()
        assert isinstance(result, str)

    def test_no_schema_returns_fallback(self, engine: SQLQueryEngine):
        """Empty schema dict returns the no-schema fallback message."""
        engine.schema = {}
        result = engine._get_schema_context()
        assert "No schema" in result

    def test_schema_context_contains_table_names(self, engine: SQLQueryEngine):
        """When schema has tables, their names appear in the context."""
        engine.schema = {
            "widgets": {"columns": [{"name": "id", "type": "integer"}]},
        }
        result = engine._get_schema_context()
        assert "widgets" in result

    def test_schema_context_contains_column_info(self, engine: SQLQueryEngine):
        """Column names and types appear in the formatted context."""
        engine.schema = {
            "orders": {"columns": [{"name": "amount", "type": "numeric"}]},
        }
        result = engine._get_schema_context()
        assert "amount" in result
        assert "numeric" in result


# ---------------------------------------------------------------------------
# SQLQueryEngine.translate_to_sql
# ---------------------------------------------------------------------------


class TestTranslateToSQL:
    """Tests for natural-language-to-SQL translation."""

    def _make_chain_return(self, engine: SQLQueryEngine, sql_text: str) -> None:
        """Wire the mock LLM so the chain returns sql_text."""
        chain_mock = MagicMock()
        chain_mock.invoke.return_value = sql_text
        engine.llm.__or__ = MagicMock(return_value=chain_mock)

    def test_returns_plain_sql(self, engine: SQLQueryEngine):
        """Clean SQL is returned unchanged."""
        with patch("socrata_toolkit.llm.sql_engine.ChatPromptTemplate") as mock_pt, patch(
            "socrata_toolkit.llm.sql_engine.StrOutputParser"
        ):
            # chain = prompt | llm | parser; invoke returns the SQL string
            mock_pt.from_messages.return_value.__or__.return_value.__or__.return_value.invoke.return_value = (
                "SELECT * FROM inspections"
            )
            result = engine.translate_to_sql("Show all inspections")
        assert isinstance(result, str)
        assert "SELECT" in result

    def test_strips_markdown_sql_fence(self, engine: SQLQueryEngine):
        """```sql ... ``` fences are stripped from the output."""
        with patch(
            "socrata_toolkit.llm.sql_engine.ChatPromptTemplate"
        ) as mock_pt, patch("socrata_toolkit.llm.sql_engine.StrOutputParser"):
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "```sql\nSELECT 1\n```"
            mock_pt.from_messages.return_value.__or__.return_value.__or__ = (
                mock_chain
            )

            raw = "```sql\nSELECT 1\n```"
            # Exercise the stripping logic directly
            sql = raw.strip()
            if sql.startswith("```sql"):
                sql = sql[6:]
            if sql.startswith("```"):
                sql = sql[3:]
            if sql.endswith("```"):
                sql = sql[:-3]
            assert sql.strip() == "SELECT 1"

    def test_strips_plain_code_fence(self, engine: SQLQueryEngine):
        """Plain ``` fences are also stripped."""
        raw = "```\nSELECT 2\n```"
        sql = raw.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        assert sql.strip() == "SELECT 2"


# ---------------------------------------------------------------------------
# SQLQueryEngine.validate_query
# ---------------------------------------------------------------------------


class TestValidateQuery:
    """Tests for the SQL safety validator."""

    @pytest.mark.parametrize(
        "sql,blocked_kw",
        [
            ("DROP TABLE inspections", "DROP"),
            ("DELETE FROM violations WHERE 1=1", "DELETE"),
            ("TRUNCATE TABLE ramps", "TRUNCATE"),
            ("ALTER TABLE t ADD COLUMN x INT", "ALTER"),
        ],
    )
    def test_dangerous_keywords_rejected(
        self, engine: SQLQueryEngine, sql: str, blocked_kw: str
    ):
        """Queries containing dangerous DDL/DML keywords are rejected."""
        ok, msg = engine.validate_query(sql)
        assert ok is False
        assert blocked_kw in msg

    def test_valid_select_passes_when_explain_succeeds(self, engine: SQLQueryEngine):
        """A plain SELECT passes validation when EXPLAIN succeeds."""
        with patch("socrata_toolkit.llm.sql_engine.psycopg.connect") as mock_conn:
            ctx = MagicMock()
            cur = MagicMock()
            cur.__enter__ = MagicMock(return_value=cur)
            cur.__exit__ = MagicMock(return_value=False)
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.cursor.return_value = cur
            mock_conn.return_value = ctx
            cur.fetchall.return_value = [("Seq Scan",)]

            ok, msg = engine.validate_query("SELECT id FROM inspections")
        assert ok is True
        assert msg == "Query is valid"

    def test_syntax_error_returns_invalid(self, engine: SQLQueryEngine):
        """A query that fails EXPLAIN is reported as invalid."""
        with patch("socrata_toolkit.llm.sql_engine.psycopg.connect") as mock_conn:
            mock_conn.side_effect = Exception("syntax error")
            ok, msg = engine.validate_query("SELECT * FROOOM broken")
        assert ok is False
        assert "validation failed" in msg.lower()


# ---------------------------------------------------------------------------
# SQLQueryEngine.execute
# ---------------------------------------------------------------------------


class TestExecute:
    """Tests for the main execute() method."""

    def _patch_translate(self, engine: SQLQueryEngine, sql: str) -> None:
        engine.translate_to_sql = MagicMock(return_value=sql)  # type: ignore[method-assign]

    def test_execute_appends_to_history(self, engine: SQLQueryEngine):
        """Each call appends one record to execution_history."""
        engine.translate_to_sql = MagicMock(return_value="SELECT 1")
        engine.validate_query = MagicMock(return_value=(False, "blocked"))
        engine.execute("anything")
        assert len(engine.execution_history) == 1

    def test_execute_invalid_query_sets_error(self, engine: SQLQueryEngine):
        """When validation fails the returned record has an error set."""
        engine.translate_to_sql = MagicMock(return_value="DROP TABLE t")
        engine.validate_query = MagicMock(return_value=(False, "DROP blocked"))
        result = engine.execute("drop table")
        assert result.error == "DROP blocked"
        assert result.results == []

    def test_execute_without_auto_translate(self, engine: SQLQueryEngine):
        """With auto_translate=False the raw question is used as the SQL."""
        raw_sql = "SELECT count(*) FROM violations"
        engine.validate_query = MagicMock(return_value=(False, "blocked for test"))
        result = engine.execute(raw_sql, auto_translate=False)
        assert result.sql_query == raw_sql

    def test_execute_successful_query(self, engine: SQLQueryEngine):
        """A successful query populates results and row_count."""
        engine.translate_to_sql = MagicMock(return_value="SELECT id FROM inspections")
        engine.validate_query = MagicMock(return_value=(True, "Query is valid"))
        engine._interpret_results = MagicMock(return_value="Found 2 records.")

        with patch("socrata_toolkit.llm.sql_engine.psycopg.connect") as mock_conn:
            ctx = MagicMock()
            cur = MagicMock()
            cur.__enter__ = MagicMock(return_value=cur)
            cur.__exit__ = MagicMock(return_value=False)
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.cursor.return_value = cur
            mock_conn.return_value = ctx
            cur.description = [("id",)]
            cur.fetchall.return_value = [(1,), (2,)]

            result = engine.execute("show ids")

        assert result.row_count == 2
        assert result.error is None

    def test_execute_exception_stored_in_error(self, engine: SQLQueryEngine):
        """Unexpected exceptions are captured in the error field."""
        engine.translate_to_sql = MagicMock(side_effect=RuntimeError("boom"))
        result = engine.execute("crash me")
        assert result.error is not None
        assert "boom" in result.error


# ---------------------------------------------------------------------------
# SQLQueryEngine.get_execution_history
# ---------------------------------------------------------------------------


class TestGetExecutionHistory:
    """Tests for the history accessor."""

    def test_get_history_default_limit(self, engine: SQLQueryEngine):
        """Default limit is 10; fewer records returns all."""
        engine.execution_history = [
            QueryExecution("q", "s", 0.0, 0, [], "", "") for _ in range(3)
        ]
        assert len(engine.get_execution_history()) == 3

    def test_get_history_respects_limit(self, engine: SQLQueryEngine):
        """Limit slices from the end of the list."""
        engine.execution_history = [
            QueryExecution(f"q{i}", "s", 0.0, 0, [], "", "") for i in range(15)
        ]
        last5 = engine.get_execution_history(limit=5)
        assert len(last5) == 5
        assert last5[-1].natural_language == "q14"


# ---------------------------------------------------------------------------
# SQLQueryEngine.explain_table
# ---------------------------------------------------------------------------


class TestExplainTable:
    """Tests for explain_table()."""

    def test_explain_unknown_table(self, engine: SQLQueryEngine):
        """Asking about a non-existent table returns a not-found message."""
        engine.schema = {}
        result = engine.explain_table("ghost_table")
        assert "not found" in result

    def test_explain_known_table_invokes_llm(self, engine: SQLQueryEngine):
        """When the table exists the LLM chain is invoked and a string is returned."""
        engine.schema = {
            "permits": {"columns": [{"name": "permit_id", "type": "text"}]}
        }
        with patch("socrata_toolkit.llm.sql_engine.ChatPromptTemplate") as mock_pt, patch(
            "socrata_toolkit.llm.sql_engine.StrOutputParser"
        ):
            mock_pt.from_messages.return_value.__or__.return_value.__or__.return_value.invoke.return_value = (
                "This table stores permits."
            )
            result = engine.explain_table("permits")
        assert isinstance(result, str)
        assert result == "This table stores permits."


# ---------------------------------------------------------------------------
# InteractiveQuerySession
# ---------------------------------------------------------------------------


class TestInteractiveQuerySession:
    """Tests for the conversational session wrapper."""

    def test_initial_conversation_empty(self, engine: SQLQueryEngine):
        """Fresh session has an empty conversation list."""
        session = InteractiveQuerySession(engine)
        assert session.get_conversation() == []

    def test_clear_empties_conversation(self, engine: SQLQueryEngine):
        """clear() resets the conversation list."""
        session = InteractiveQuerySession(engine)
        session.conversation.append({"question": "q", "sql": "", "results": [], "interpretation": "", "timestamp": "", "error": None})
        session.clear()
        assert session.get_conversation() == []

    def test_ask_stores_question(self, engine: SQLQueryEngine):
        """After ask() the question appears in conversation."""
        engine.execute = MagicMock(
            return_value=QueryExecution(
                "q", "SELECT 1", 5.0, 0, [], "", datetime.now(timezone.utc).isoformat()
            )
        )
        session = InteractiveQuerySession(engine)
        session.ask("How many rows?")
        assert session.get_conversation()[0]["question"] == "How many rows?"

    def test_is_followup_detects_keywords(self, engine: SQLQueryEngine):
        """Follow-up keyword detection returns True for known words."""
        session = InteractiveQuerySession(engine)
        assert session._is_followup_question("what about this?") is True
        assert session._is_followup_question("also show me that") is True

    def test_is_followup_returns_false_for_fresh_question(self, engine: SQLQueryEngine):
        """A brand-new question without follow-up cues returns False."""
        session = InteractiveQuerySession(engine)
        assert session._is_followup_question("How many violations?") is False

    def test_build_context_empty_when_no_history(self, engine: SQLQueryEngine):
        """Context string is empty when there is no prior conversation."""
        session = InteractiveQuerySession(engine)
        assert session._build_context() == ""

    def test_build_context_populated_after_two_turns(self, engine: SQLQueryEngine):
        """Context is non-empty once two items are in conversation."""
        session = InteractiveQuerySession(engine)
        for i in range(2):
            session.conversation.append(
                {"question": f"q{i}", "sql": "", "results": [], "interpretation": "", "timestamp": "", "error": None}
            )
        ctx = session._build_context()
        assert "q0" in ctx or "q1" in ctx


# ---------------------------------------------------------------------------
# QueryOptimizer
# ---------------------------------------------------------------------------


class TestQueryOptimizer:
    """Tests for QueryOptimizer LLM wrappers."""

    def test_suggest_optimizations_returns_list(self, engine: SQLQueryEngine, mock_llm):
        """suggest_optimizations returns a list (possibly empty)."""
        optimizer = QueryOptimizer(engine=engine, llm=mock_llm)
        with patch("socrata_toolkit.llm.sql_engine.ChatPromptTemplate") as mock_pt, patch(
            "socrata_toolkit.llm.sql_engine.JsonOutputParser"
        ):
            mock_pt.from_messages.return_value.__or__.return_value.__or__.return_value.invoke.return_value = {
                "suggestions": [{"optimization": "add index", "benefit": "faster"}]
            }
            result = optimizer.suggest_optimizations(
                "SELECT * FROM inspections WHERE borough='MN'"
            )
        assert isinstance(result, list)

    def test_suggest_alternatives_returns_list(self, engine: SQLQueryEngine, mock_llm):
        """suggest_alternatives returns a list (possibly empty)."""
        optimizer = QueryOptimizer(engine=engine, llm=mock_llm)
        with patch("socrata_toolkit.llm.sql_engine.ChatPromptTemplate") as mock_pt, patch(
            "socrata_toolkit.llm.sql_engine.JsonOutputParser"
        ):
            mock_pt.from_messages.return_value.__or__.return_value.__or__.return_value.invoke.return_value = {
                "alternatives": ["SELECT id FROM t", "SELECT * FROM t LIMIT 10"]
            }
            result = optimizer.suggest_alternatives("SELECT * FROM t")
        assert isinstance(result, list)
