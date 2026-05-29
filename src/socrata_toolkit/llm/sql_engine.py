"""
Wolfram-like SQL Query Engine using LangChain.

Natural language to SQL translation with:
- Automatic schema understanding
- Query validation and optimization
- Live database execution
- Result interpretation and explanation
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg
from langchain_core.language_model import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


@dataclass
class QueryExecution:
    """Record of a query execution."""
    natural_language: str
    sql_query: str
    execution_time_ms: float
    row_count: int
    results: list[dict[str, Any]]
    interpretation: str
    timestamp: str
    error: str | None = None


class SQLQueryEngine:
    """
    Translates natural language questions to SQL and executes them.

    Features:
    - Automatic schema introspection
    - Natural language to SQL with LLM
    - Query validation and safety checks
    - Result interpretation
    - Execution history tracking
    """

    def __init__(
        self,
        dsn: str,
        llm: BaseLanguageModel,
        max_results: int = 1000,
        enable_explain: bool = True,
    ):
        """
        Initialize SQL query engine.

        Args:
            dsn: PostgreSQL connection string
            llm: LangChain LLM instance
            max_results: Maximum rows to return from queries
            enable_explain: Whether to explain results
        """
        self.dsn = dsn
        self.llm = llm
        self.max_results = max_results
        self.enable_explain = enable_explain
        self.execution_history: list[QueryExecution] = []

        # Cache schema information
        self.schema: dict[str, Any] = {}
        self._refresh_schema()

    def _refresh_schema(self) -> None:
        """Load database schema."""
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Get tables
                    cur.execute("""
                        SELECT tablename FROM pg_tables
                        WHERE schemaname = 'public'
                        ORDER BY tablename
                    """)
                    tables = {row[0]: {} for row in cur.fetchall()}

                    # Get columns for each table
                    for table_name in tables:
                        cur.execute("""
                            SELECT column_name, data_type
                            FROM information_schema.columns
                            WHERE table_name = %s
                            ORDER BY ordinal_position
                        """, (table_name,))
                        tables[table_name]["columns"] = [
                            {"name": row[0], "type": row[1]}
                            for row in cur.fetchall()
                        ]

                    self.schema = tables
                    logger.info(f"Schema refreshed: {len(tables)} tables")
        except Exception as e:
            logger.error(f"Failed to refresh schema: {e}")
            self.schema = {}

    def _get_schema_context(self) -> str:
        """Format schema for LLM context."""
        if not self.schema:
            return "No schema information available"

        schema_lines = ["Database Schema:"]
        for table_name, table_info in self.schema.items():
            schema_lines.append(f"\nTable: {table_name}")
            if "columns" in table_info:
                for col in table_info["columns"]:
                    schema_lines.append(f"  - {col['name']} ({col['type']})")

        return "\n".join(schema_lines)

    def translate_to_sql(self, question: str) -> str:
        """
        Translate natural language question to SQL.

        Args:
            question: Natural language question

        Returns:
            SQL query string
        """
        schema_context = self._get_schema_context()

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert SQL developer.
Convert natural language questions to PostgreSQL queries.
Return ONLY the SQL query, no explanation.
Use LIMIT to restrict results."""),
            ("human", f"""{schema_context}

Question: {question}

Generate a PostgreSQL query. Return only the SQL, no markdown or explanation.""")
        ])

        chain = prompt | self.llm | StrOutputParser()
        sql = chain.invoke({})

        # Clean up response (remove markdown code blocks if present)
        sql = sql.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]

        return sql.strip()

    def validate_query(self, sql: str) -> tuple[bool, str]:
        """
        Validate SQL query for safety.

        Args:
            sql: SQL query to validate

        Returns:
            Tuple of (is_valid, message)
        """
        # Check for dangerous operations
        dangerous_keywords = [
            "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE INDEX",
            "VACUUM", "REINDEX", "ANALYZE"
        ]

        sql_upper = sql.upper()
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"Query contains dangerous operation: {keyword}"

        # Check query syntax with a dry run
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # EXPLAIN without executing
                    cur.execute(f"EXPLAIN {sql}")
                    cur.fetchall()
            return True, "Query is valid"
        except Exception as e:
            return False, f"Query validation failed: {str(e)}"

    def execute(self, question: str, auto_translate: bool = True) -> QueryExecution:
        """
        Execute a natural language query.

        Args:
            question: Natural language question
            auto_translate: Whether to translate question to SQL

        Returns:
            QueryExecution record
        """
        execution_record = QueryExecution(
            natural_language=question,
            sql_query="",
            execution_time_ms=0.0,
            row_count=0,
            results=[],
            interpretation="",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        try:
            # Translate to SQL if needed
            if auto_translate:
                sql = self.translate_to_sql(question)
                logger.info(f"Translated question to SQL: {sql}")
            else:
                sql = question

            execution_record.sql_query = sql

            # Validate query
            is_valid, message = self.validate_query(sql)
            if not is_valid:
                execution_record.error = message
                self.execution_history.append(execution_record)
                return execution_record

            # Execute query
            start_time = datetime.now(timezone.utc)
            results = []

            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(f"{sql} LIMIT {self.max_results}")

                    # Get column names
                    if cur.description:
                        columns = [desc[0] for desc in cur.description]

                        # Fetch results
                        for row in cur.fetchall():
                            results.append(dict(zip(columns, row, strict=False)))

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            execution_record.results = results
            execution_record.row_count = len(results)
            execution_record.execution_time_ms = execution_time

            # Interpret results
            if self.enable_explain and results:
                execution_record.interpretation = self._interpret_results(
                    question, results
                )

            logger.info(f"Query executed successfully: {len(results)} rows in {execution_time:.1f}ms")

        except Exception as e:
            execution_record.error = str(e)
            logger.error(f"Query execution failed: {e}")

        self.execution_history.append(execution_record)
        return execution_record

    def _interpret_results(self, question: str, results: list[dict[str, Any]]) -> str:
        """
        Generate interpretation of query results.

        Args:
            question: Original question
            results: Query results

        Returns:
            Interpretation text
        """
        # Summarize results for LLM
        sample_results = json.dumps(results[:5], indent=2, default=str)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a data analyst. Explain query results in clear, business-friendly language.
Be concise and highlight key findings."""),
            ("human", f"""Question: {question}

Results summary (showing first 5 of {len(results)} rows):
{sample_results}

Provide a 2-3 sentence interpretation of what these results show.""")
        ])

        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({})

    def get_execution_history(self, limit: int = 10) -> list[QueryExecution]:
        """Get recent query executions."""
        return self.execution_history[-limit:]

    def explain_table(self, table_name: str) -> str:
        """
        Generate explanation of a table.

        Args:
            table_name: Name of table to explain

        Returns:
            Explanation text
        """
        if table_name not in self.schema:
            return f"Table '{table_name}' not found"

        table_info = self.schema[table_name]
        columns_str = ", ".join(
            f"{col['name']} ({col['type']})"
            for col in table_info.get("columns", [])
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a database documentation expert."),
            ("human", f"""Explain this database table for an analyst:

Table: {table_name}
Columns: {columns_str}

Provide a 2-3 sentence explanation of what this table contains.""")
        ])

        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({})


class InteractiveQuerySession:
    """
    Manages an interactive query session with conversation context.

    Keeps track of previously asked questions and their context
    to support follow-up questions.
    """

    def __init__(self, engine: SQLQueryEngine):
        """Initialize interactive session."""
        self.engine = engine
        self.conversation: list[dict[str, Any]] = []

    def ask(self, question: str) -> dict[str, Any]:
        """
        Ask a question in context of conversation history.

        Args:
            question: Natural language question

        Returns:
            Dict with query, results, and interpretation
        """
        # Build context from previous questions
        context = self._build_context()

        # Enhance question with context if it's a follow-up
        enhanced_question = question
        if context and self._is_followup_question(question):
            enhanced_question = f"{context}\n\nFollow-up question: {question}"

        # Execute query
        execution = self.engine.execute(enhanced_question)

        # Store in conversation
        self.conversation.append({
            "question": question,
            "sql": execution.sql_query,
            "results": execution.results,
            "interpretation": execution.interpretation,
            "timestamp": execution.timestamp,
            "error": execution.error,
        })

        return self.conversation[-1]

    def _build_context(self) -> str:
        """Build context from previous questions."""
        if len(self.conversation) < 2:
            return ""

        context_lines = ["Previous context:"]
        for item in self.conversation[-3:]:  # Last 3 questions
            context_lines.append(f"- Q: {item['question']}")
            if item['results']:
                context_lines.append(f"  Result: {len(item['results'])} rows")

        return "\n".join(context_lines)

    def _is_followup_question(self, question: str) -> bool:
        """Detect if question is a follow-up."""
        followup_keywords = ["also", "then", "what about", "furthermore", "additionally", "this", "that", "those"]
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in followup_keywords)

    def get_conversation(self) -> list[dict[str, Any]]:
        """Get full conversation history."""
        return self.conversation

    def clear(self) -> None:
        """Clear conversation history."""
        self.conversation.clear()


class QueryOptimizer:
    """
    Suggests query optimizations and alternative formulations.
    """

    def __init__(self, engine: SQLQueryEngine, llm: BaseLanguageModel):
        """Initialize optimizer."""
        self.engine = engine
        self.llm = llm

    def suggest_optimizations(self, sql: str) -> list[dict[str, str]]:
        """
        Suggest optimizations for a query.

        Args:
            sql: SQL query to optimize

        Returns:
            List of optimization suggestions
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a SQL performance expert.
Analyze queries and suggest specific optimizations.
Return JSON with suggestions."""),
            ("human", f"""Analyze this PostgreSQL query for optimization:

{sql}

Return JSON format:
{{"suggestions": [{{"optimization": "description", "benefit": "expected improvement"}}]}}""")
        ])

        chain = prompt | self.llm | JsonOutputParser()
        result = chain.invoke({})
        return result.get("suggestions", [])

    def suggest_alternatives(self, sql: str) -> list[str]:
        """
        Suggest alternative query formulations.

        Args:
            sql: Original query

        Returns:
            List of alternative SQL queries
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a SQL expert. Suggest alternative query formulations."),
            ("human", f"""Given this query:

{sql}

Suggest 2-3 alternative ways to write the same query.
Return as JSON array: {{"alternatives": ["query1", "query2"]}}""")
        ])

        chain = prompt | self.llm | JsonOutputParser()
        result = chain.invoke({})
        return result.get("alternatives", [])
