"""MotherDuck cloud backend integration with local DuckDB fallback.

Enables seamless switching between local DuckDB and MotherDuck cloud,
with automatic SQL compatibility validation.

Key constraints (per MotherDuck docs):
- MotherDuck can lag upstream DuckDB by 1-2 releases
- Avoid VARIANT, native GEOMETRY, MERGE INTO, recent date_trunc changes
- Postgres endpoint mode differs from native DuckDB mode
- snapshot/restore are MotherDuck operational commands, not analytical
- Extensions: httpfs, delta, parquet pre-installed; others may vary
"""
import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import duckdb

logger = logging.getLogger(__name__)

@dataclass
class CompatibilityIssue:
    """SQL compatibility issue found during validation."""
    pattern: str
    severity: str  # "warning" | "error"
    reason: str
    suggestion: str

class MotherDuckValidator:
    """Validate SQL for MotherDuck compatibility.

    Checks for patterns that work in DuckDB but may fail on MotherDuck.
    """

    # Functions/features that differ between DuckDB and MotherDuck
    COMPATIBILITY_RULES = [
        {
            "pattern": r"\bVARIANT\b",
            "severity": "error",
            "reason": "VARIANT type not available in MotherDuck; use VARCHAR instead",
            "suggestion": "Replace VARIANT with VARCHAR or STRUCT",
        },
        {
            "pattern": r"\bGEOMETRY\b",
            "severity": "error",
            "reason": "Native GEOMETRY not available in MotherDuck; use spatial extension",
            "suggestion": "Use spatial extension functions or store as WKT/WKB",
        },
        {
            "pattern": r"\bMERGE\s+INTO\b",
            "severity": "error",
            "reason": "MERGE INTO not available in MotherDuck",
            "suggestion": "Use INSERT/UPDATE separately or upsert pattern",
        },
        {
            "pattern": r"date_trunc\s*\(\s*['\"]decade['\"]",
            "severity": "warning",
            "reason": "date_trunc('decade', ...) behavior may differ; added in recent DuckDB",
            "suggestion": "Use explicit date math: DATE_TRUNC('year', date) - INTERVAL '5 years'",
        },
        {
            "pattern": r"\bLOAD\s+\w+\s*;",
            "severity": "warning",
            "reason": "LOAD statement is client-only; may not work in MotherDuck server mode",
            "suggestion": "Extensions are pre-loaded in MotherDuck; remove LOAD statement",
        },
        {
            "pattern": r"CREATE\s+TEMPORARY\s+TABLE",
            "severity": "warning",
            "reason": "Temporary tables have different lifetime in MotherDuck cloud",
            "suggestion": "Use persistent tables or session tables (CREATE TEMP TABLE)",
        },
        {
            "pattern": r"READ_CSV_AUTO\s*\(",
            "severity": "warning",
            "reason": "File paths in MotherDuck must use S3 or DuckDB paths, not local FS",
            "suggestion": "Use httpfs extension with S3 paths or DuckDB paths",
        },
    ]

    def validate(self, sql: str) -> list[CompatibilityIssue]:
        """Validate SQL for MotherDuck compatibility.

        Args:
            sql: SQL statement to validate

        Returns:
            List of compatibility issues found (empty if all clear)
        """
        issues = []

        for rule in self.COMPATIBILITY_RULES:
            if re.search(rule["pattern"], sql, re.IGNORECASE):
                issues.append(
                    CompatibilityIssue(
                        pattern=rule["pattern"],
                        severity=rule["severity"],
                        reason=rule["reason"],
                        suggestion=rule["suggestion"],
                    )
                )

        return issues

    def is_compatible(self, sql: str) -> bool:
        """Check if SQL is compatible with MotherDuck.

        Returns True only if no errors (warnings are allowed).
        """
        issues = self.validate(sql)
        return not any(issue.severity == "error" for issue in issues)

class DuckDBConnection:
    """Wrapper for local DuckDB connection."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self.is_motherduck = False
        self.validator = MotherDuckValidator()

    def execute(self, sql: str, validate: bool = True):
        """Execute SQL with optional MotherDuck compatibility check.

        Args:
            sql: SQL to execute
            validate: If True, validate against MotherDuck compatibility rules

        Returns:
            Query result
        """
        if validate:
            issues = self.validator.validate(sql)
            if issues:
                for issue in issues:
                    level = "error" if issue.severity == "error" else "warning"
                    logger.log(
                        logging.ERROR if level == "error" else logging.WARNING,
                        f"MotherDuck compatibility {issue.severity}: {issue.reason}\n"
                        f"  Suggestion: {issue.suggestion}",
                    )
                if any(i.severity == "error" for i in issues):
                    raise ValueError(
                        f"SQL contains {len([i for i in issues if i.severity == 'error'])} "
                        "MotherDuck compatibility errors"
                    )

        return self.conn.execute(sql)

    def close(self):
        """Close connection."""
        if self.conn:
            self.conn.close()

class MotherDuckConnection:
    """Wrapper for MotherDuck cloud connection.

    Requires MOTHERDUCK_TOKEN environment variable.
    Falls back to local DuckDB if token not set.
    """

    def __init__(self, token: Optional[str] = None, db_path: str = "md:"):
        """Initialize MotherDuck connection.

        Args:
            token: MotherDuck API token (defaults to MOTHERDUCK_TOKEN env var)
            db_path: Connection string (defaults to "md:" for MotherDuck)
        """
        self.token = token or os.getenv("MOTHERDUCK_TOKEN")
        self.db_path = db_path
        self.is_motherduck = bool(self.token)
        self.validator = MotherDuckValidator()

        try:
            if self.token:
                os.environ["MOTHERDUCK_TOKEN"] = self.token
                self.conn = duckdb.connect(db_path)
                logger.info("Connected to MotherDuck cloud")
            else:
                logger.warning(
                    "MOTHERDUCK_TOKEN not set; falling back to local DuckDB"
                )
                self.conn = duckdb.connect(":memory:")
                self.is_motherduck = False
        except Exception as e:
            logger.error(f"Failed to connect to MotherDuck: {e}; using local DuckDB")
            self.conn = duckdb.connect(":memory:")
            self.is_motherduck = False

    def execute(self, sql: str, validate: bool = True):
        """Execute SQL with optional MotherDuck compatibility check.

        Args:
            sql: SQL to execute
            validate: If True, validate against MotherDuck compatibility rules

        Returns:
            Query result
        """
        if validate:
            issues = self.validator.validate(sql)
            if issues:
                for issue in issues:
                    logger.log(
                        logging.ERROR if issue.severity == "error" else logging.WARNING,
                        f"MotherDuck compatibility {issue.severity}: {issue.reason}\n"
                        f"  Suggestion: {issue.suggestion}",
                    )
                if any(i.severity == "error" for i in issues):
                    raise ValueError(
                        f"SQL contains {len([i for i in issues if i.severity == 'error'])} "
                        "MotherDuck compatibility errors"
                    )

        return self.conn.execute(sql)

    def close(self):
        """Close connection."""
        if self.conn:
            self.conn.close()

def get_connection(use_motherduck: bool = True) -> DuckDBConnection | MotherDuckConnection:
    """Get DuckDB or MotherDuck connection based on configuration.

    Args:
        use_motherduck: If True, try MotherDuck; fall back to local if unavailable

    Returns:
        DuckDB or MotherDuck connection wrapper
    """
    if use_motherduck:
        return MotherDuckConnection()
    else:
        return DuckDBConnection()
