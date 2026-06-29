"""
SQL File Executor Module
Loads, validates, and executes SQL files with support for templates and conditional logic.
"""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SQLStatement:
    """Represents a single SQL statement."""
    index: int
    sql: str
    description: str = ""
    lines: Tuple[int, int] = (0, 0)  # (start_line, end_line)


class SQLExecutor:
    """
    Executes SQL files with support for:
    - Comment stripping (-- and /* */)
    - Statement separation (GO, semicolon, newline blocks)
    - Template substitution
    - Conditional blocks (-- IF schema EXISTS)
    - Error recovery
    """

    def __init__(self, sql_dir: str = "pipeline/sql"):
        """
        Initialize SQL executor.

        Args:
            sql_dir: Base directory for SQL files
        """
        self.sql_dir = Path(sql_dir)
        self.statements: List[SQLStatement] = []
        self.templates: Dict[str, str] = {}

    def load_file(self, filename: str) -> str:
        """
        Load SQL file from sql_dir.

        Args:
            filename: Filename (relative to sql_dir)

        Returns:
            Raw SQL file content
        """
        file_path = self.sql_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"SQL file not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            logger.info(f"Loaded SQL file: {filename} ({len(content)} bytes)")
            return content
        except Exception as e:
            logger.error(f"Error reading SQL file {filename}: {str(e)}")
            raise

    def strip_comments(self, sql: str) -> str:
        """
        Remove SQL comments (-- and /* */).

        Args:
            sql: SQL with comments

        Returns:
            SQL without comments
        """
        # Remove line comments (-- comment)
        sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)

        # Remove block comments (/* comment */)
        sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)

        return sql

    def split_statements(self, sql: str) -> List[str]:
        """
        Split SQL into individual statements.
        Handles GO (SQL Server), semicolon, and newline-separated blocks.

        Args:
            sql: SQL text (possibly multiple statements)

        Returns:
            List of SQL statements
        """
        # Replace GO with semicolon for uniform handling
        sql = re.sub(r"^\s*GO\s*$", ";", sql, flags=re.MULTILINE|re.IGNORECASE)

        # Split by semicolon
        statements = []
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                statements.append(statement)

        return statements

    def parse_file(self, filename: str) -> List[SQLStatement]:
        """
        Parse SQL file into separate statements with metadata.

        Args:
            filename: Filename to parse

        Returns:
            List of SQLStatement objects
        """
        raw_sql = self.load_file(filename)
        sql_clean = self.strip_comments(raw_sql)
        statements_raw = self.split_statements(sql_clean)

        statements = []
        for idx, stmt in enumerate(statements_raw):
            # Extract description from preceding comment if any
            description = f"Statement {idx + 1}"

            statements.append(
                SQLStatement(
                    index=idx,
                    sql=stmt,
                    description=description
                )
            )

        self.statements = statements
        logger.info(f"Parsed {len(statements)} SQL statements from {filename}")
        return statements

    def substitute_templates(self, sql: str, context: Optional[Dict[str, str]] = None) -> str:
        """
        Substitute template variables in SQL.

        Args:
            sql: SQL with {{variable}} placeholders
            context: Dictionary of {variable: value}

        Returns:
            SQL with substitutions applied
        """
        if not context:
            context = self.templates

        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}}
            sql = sql.replace(placeholder, value)

        return sql

    def validate_syntax(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Basic SQL syntax validation (check for unmatched quotes, parentheses).

        Args:
            sql: SQL to validate

        Returns:
            (is_valid, error_message)
        """
        # Check for unmatched single quotes
        if sql.count("'") % 2 != 0:
            return False, "Unmatched single quote"

        # Check for unmatched double quotes
        if sql.count('"') % 2 != 0:
            return False, "Unmatched double quote"

        # Check for unmatched parentheses
        open_parens = sql.count("(")
        close_parens = sql.count(")")
        if open_parens != close_parens:
            return False, f"Unmatched parentheses ({open_parens} open, {close_parens} close)"

        return True, None

    def get_statement_by_index(self, index: int) -> Optional[SQLStatement]:
        """Get statement by index."""
        return self.statements[index] if 0 <= index < len(self.statements) else None

    def get_statements_by_pattern(self, pattern: str) -> List[SQLStatement]:
        """
        Get statements matching a pattern (e.g., containing CREATE TABLE).

        Args:
            pattern: Regex pattern to search in SQL

        Returns:
            Matching statements
        """
        return [
            stmt for stmt in self.statements
            if re.search(pattern, stmt.sql, re.IGNORECASE)
        ]

    def log_statements(self):
        """Log all parsed statements."""
        logger.info("Parsed SQL statements:")
        for stmt in self.statements:
            sql_preview = stmt.sql[:60].replace("\n", " ")
            logger.info(f"  [{stmt.index}] {sql_preview}...")


# Pipeline stage executors
class PipelineStageExecutor:
    """
    Executor for pipeline stages.
    Loads and executes SQL in proper order: raw → staging → analytics → serving → validation.
    """

    PIPELINE_STAGES = [
        ("01_raw_schema.sql", "Load raw data from Socrata + Parquet cache"),
        ("02_staging_schema.sql", "Deduplicate and type-cast to staging"),
        ("03_analytics_schemas.sql", "Build 5 domain schemas"),
        ("04_serving_metrics.sql", "Compute 255 Metric records"),
        ("05_verification_gates.sql", "Run verification gates"),
    ]

    def __init__(self, bridge, sql_dir: str = "pipeline/sql"):
        """
        Initialize pipeline executor.

        Args:
            bridge: MotherDuckBridge instance
            sql_dir: Base directory for SQL files
        """
        self.bridge = bridge
        self.executor = SQLExecutor(sql_dir)

    def execute_stage(self, filename: str, skip_validation: bool = False):
        """
        Execute a single pipeline stage.

        Args:
            filename: SQL filename
            skip_validation: Skip syntax validation

        Returns:
            (success, message)
        """
        logger.info(f"Executing stage: {filename}")

        try:
            # Parse SQL file
            statements = self.executor.parse_file(filename)
            logger.info(f"Parsed {len(statements)} statements")

            # Execute each statement
            for stmt in statements:
                # Validate syntax
                if not skip_validation:
                    valid, error = self.executor.validate_syntax(stmt.sql)
                    if not valid:
                        logger.error(f"Statement {stmt.index} validation failed: {error}")
                        return False, f"Validation error: {error}"

                # Execute
                logger.debug(f"Executing statement {stmt.index}: {stmt.sql[:80]}...")
                result = self.bridge.execute_sql(stmt.sql)

                if not result.success:
                    logger.error(f"Statement {stmt.index} failed: {result.error}")
                    return False, f"Execution error at statement {stmt.index}: {result.error}"

                logger.info(f"Statement {stmt.index} succeeded ({result.rows_affected} rows)")

            logger.info(f"Stage {filename} completed successfully")
            return True, f"Stage {filename} completed successfully"

        except Exception as e:
            logger.error(f"Stage {filename} failed with exception: {str(e)}")
            return False, f"Exception: {str(e)}"

    def execute_pipeline(self) -> Dict[str, Tuple[bool, str]]:
        """
        Execute all pipeline stages in order.

        Returns:
            Dictionary of {stage: (success, message)}
        """
        results = {}

        for filename, description in self.PIPELINE_STAGES:
            logger.info(f"Stage: {description}")
            success, message = self.execute_stage(filename)
            results[filename] = (success, message)

            if not success:
                logger.error(f"Pipeline failed at {filename}: {message}")
                break

        return results


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    executor = SQLExecutor("pipeline/sql")

    # Test comment stripping
    test_sql = """
    -- This is a comment
    CREATE TABLE test (id INTEGER);
    /* Block comment */ SELECT * FROM test;
    """
    cleaned = executor.strip_comments(test_sql)
    print("Cleaned SQL:")
    print(cleaned)

    # Test statement splitting
    statements = executor.split_statements(cleaned)
    print(f"\nFound {len(statements)} statements:")
    for i, stmt in enumerate(statements):
        print(f"  {i}: {stmt[:50]}...")
