"""
Schema Registry Module - NYC DOT Sidewalk Toolkit

Purpose: Track schema versions, detect drift, enforce contracts on ingested datasets.
This module maintains version history, detects schema changes, and alerts data engineers
to breaking changes that could impact downstream transformations and KPI computations.

Standards: Python 3.9+, type hints, comprehensive docstrings, audit trail logging
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Classification of schema changes per their impact on downstream systems."""

    COLUMN_ADDITION = "addition"  # Non-breaking: new optional column
    COLUMN_DELETION = "deletion"  # Breaking: column no longer available
    TYPE_CHANGE = "type_change"  # Breaking: column type changed
    RENAME = "rename"  # Breaking: column renamed
    NULL_CONSTRAINT_CHANGE = "null_constraint_change"  # Breaking: nullability changed
    POSITION_CHANGE = "position_change"  # Non-breaking: column order changed


@dataclass
class ColumnSchema:
    """Represents a single column schema definition with metadata.

    Attributes:
        name: Column name
        dtype: Pandas/NumPy dtype as string (e.g., "int64", "object", "float64")
        nullable: Whether the column allows NULL values
        position: Zero-based column order
        sample_value: Example value from the data for debugging
    """

    name: str
    dtype: str
    nullable: bool
    position: int
    sample_value: Optional[str] = None


@dataclass
class DatasetSchema:
    """Complete schema snapshot for a dataset.

    Attributes:
        dataset_id: Unique identifier for the dataset (e.g., Socrata resource ID)
        version: Monotonically increasing version number
        columns: Dict mapping column name to ColumnSchema
        captured_at: Timestamp when schema was captured
        row_count: Number of rows in dataset at capture time
        metadata: Additional metadata (e.g., source URL, description)
    """

    dataset_id: str
    version: int
    columns: dict[str, ColumnSchema]
    captured_at: datetime
    row_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert schema to serializable dictionary."""
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "columns": {k: asdict(v) for k, v in self.columns.items()},
            "captured_at": self.captured_at.isoformat(),
            "row_count": self.row_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetSchema:
        """Construct schema from serialized dictionary."""
        columns = {
            k: ColumnSchema(**v) for k, v in data.get("columns", {}).items()
        }
        return cls(
            dataset_id=data["dataset_id"],
            version=data["version"],
            columns=columns,
            captured_at=datetime.fromisoformat(data["captured_at"]),
            row_count=data["row_count"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class SchemaChange:
    """Represents a detected schema difference between two versions.

    Attributes:
        change_type: Type of change (from ChangeType enum)
        field_name: Name of the column that changed
        old_value: Previous value (dtype, name, nullable setting)
        new_value: Current value
        is_breaking: True if this change could break downstream pipelines
        description: Human-readable description of the change
    """

    change_type: ChangeType
    field_name: str
    old_value: Any
    new_value: Any
    is_breaking: bool
    description: str


class BreakingChangeAlert(Exception):
    """Alert notification for breaking schema changes.

    Raised when schema changes would impact production pipelines, KPI computation,
    or data quality gates. Triggers incident notifications.

    Attributes:
        dataset_id: Affected dataset
        from_version: Previous schema version
        to_version: Current schema version
        breaking_changes: List of breaking changes detected
        timestamp: When alert was generated
        recommendation: Suggested remediation action
    """

    def __init__(
        self,
        dataset_id: str,
        from_version: int,
        to_version: int,
        breaking_changes: list[SchemaChange],
        timestamp: datetime,
        recommendation: str = "",
    ):
        """Initialize breaking change alert exception.

        Args:
            dataset_id: Affected dataset ID
            from_version: Previous schema version number
            to_version: Current schema version number
            breaking_changes: List of SchemaChange objects that are breaking
            timestamp: When the alert was generated
            recommendation: Suggested remediation action
        """
        self.dataset_id = dataset_id
        self.from_version = from_version
        self.to_version = to_version
        self.breaking_changes = breaking_changes
        self.timestamp = timestamp
        self.recommendation = recommendation
        super().__init__(str(self))

    def __str__(self) -> str:
        """Human-readable alert message."""
        changes_str = "\n".join(
            [
                f"  - {change.field_name}: {change.description}"
                for change in self.breaking_changes
            ]
        )
        return (
            f"BREAKING SCHEMA CHANGE ALERT\n"
            f"Dataset: {self.dataset_id}\n"
            f"Version: {self.from_version} → {self.to_version}\n"
            f"Detected at: {self.timestamp.isoformat()}\n"
            f"Changes:\n{changes_str}\n"
            f"Recommendation: {self.recommendation}"
        )


class SchemaRegistry:
    """Manages schema versions, detects drift, enforces contracts.

    Maintains version history of ingested datasets, detects schema changes
    between versions, classifies breaking vs. non-breaking changes, and
    raises alerts for production violations.

    Usage:
        registry = SchemaRegistry(storage_dir="schema_registry/")
        schema = SchemaRegistry.extract_schema_from_dataframe(df, "my-dataset-id")
        registry.register_schema("my-dataset-id", schema)

        # Later, check for drift:
        current_df = pd.read_csv("new_data.csv")
        current_schema = SchemaRegistry.extract_schema_from_dataframe(current_df, "my-dataset-id")
        changes = registry.detect_drift("my-dataset-id", current_schema)
        if any(c.is_breaking for c in changes):
            raise BreakingChangeAlert(...)
    """

    def __init__(self, storage_dir: str = "schema_registry/"):
        """Initialize the schema registry with JSON file storage.

        Args:
            storage_dir: Directory path for storing schema version history
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._initialize_audit_log()

    def _initialize_audit_log(self) -> None:
        """Initialize audit log file for tracking all schema changes."""
        self.audit_log_path = self.storage_dir / "schema_changes_audit.jsonl"
        if not self.audit_log_path.exists():
            self.audit_log_path.touch()

    def _log_change(
        self, dataset_id: str, operation: str, details: dict[str, Any]
    ) -> None:
        """Log a schema change to audit trail.

        Args:
            dataset_id: Dataset identifier
            operation: Operation type (register, detect_drift, alert_issued)
            details: Change details as dictionary
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "dataset_id": dataset_id,
            "operation": operation,
            **details,
        }
        with open(self.audit_log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        logger.info(f"Schema audit logged: {dataset_id} {operation}")

    @staticmethod
    def extract_schema_from_dataframe(
        df: pd.DataFrame, dataset_id: str, metadata: Optional[dict[str, Any]] = None
    ) -> DatasetSchema:
        """Extract schema from a Pandas DataFrame.

        Introspects the DataFrame to build a schema definition including
        column names, dtypes, nullability, and sample values for debugging.

        Args:
            df: Input DataFrame to analyze
            dataset_id: Unique dataset identifier
            metadata: Optional metadata dict (source URL, description, etc.)

        Returns:
            DatasetSchema object representing the DataFrame schema

        Example:
            >>> df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
            >>> schema = SchemaRegistry.extract_schema_from_dataframe(df, "test-data")
            >>> schema.columns["id"].dtype
            'int64'
        """
        columns: dict[str, ColumnSchema] = {}

        for position, col_name in enumerate(df.columns):
            col_data = df[col_name]
            null_count = col_data.isna().sum()
            nullable = null_count > 0

            # Get sample value for debugging
            non_null_values = col_data.dropna()
            sample_value = (
                str(non_null_values.iloc[0]) if len(non_null_values) > 0 else None
            )

            columns[col_name] = ColumnSchema(
                name=col_name,
                dtype=str(col_data.dtype),
                nullable=nullable,
                position=position,
                sample_value=sample_value,
            )

        metadata = metadata or {}
        return DatasetSchema(
            dataset_id=dataset_id,
            version=1,
            columns=columns,
            captured_at=datetime.utcnow(),
            row_count=len(df),
            metadata=metadata,
        )

    def register_schema(self, schema: DatasetSchema, increment_version: bool = True) -> None:
        """Register a new schema version for a dataset.

        Persists the schema to JSON file and maintains version history.
        If increment_version is True, automatically increments the version number.

        Args:
            schema: DatasetSchema to register
            increment_version: If True, auto-increment version based on history

        Raises:
            ValueError: If dataset_id is invalid

        Example:
            >>> schema = SchemaRegistry.extract_schema_from_dataframe(df, "my-dataset")
            >>> registry.register_schema(schema)
        """
        if not schema.dataset_id:
            raise ValueError("schema.dataset_id cannot be empty")

        # Load existing schemas to determine next version
        history = self._load_schema_history(schema.dataset_id)
        if increment_version and history:
            schema.version = max(s.version for s in history) + 1

        # Persist schema version
        history_path = self.storage_dir / f"{schema.dataset_id}_history.json"
        all_versions = [s.to_dict() for s in history] + [schema.to_dict()]

        with open(history_path, "w") as f:
            json.dump(all_versions, f, indent=2)

        logger.info(
            f"Schema registered: {schema.dataset_id} v{schema.version} "
            f"({len(schema.columns)} columns, {schema.row_count} rows)"
        )
        self._log_change(
            schema.dataset_id,
            "register_schema",
            {"version": schema.version, "column_count": len(schema.columns)},
        )

    def get_schema_version(
        self, dataset_id: str, version: Optional[int] = None
    ) -> Optional[DatasetSchema]:
        """Retrieve a specific schema version for a dataset.

        Args:
            dataset_id: Dataset identifier
            version: Specific version to retrieve. If None, returns latest.

        Returns:
            DatasetSchema if found, None otherwise

        Example:
            >>> latest_schema = registry.get_schema_version("my-dataset")
            >>> v1_schema = registry.get_schema_version("my-dataset", version=1)
        """
        history = self._load_schema_history(dataset_id)
        if not history:
            return None

        if version is None:
            return history[-1]  # Return latest version

        matching = [s for s in history if s.version == version]
        return matching[0] if matching else None

    def detect_drift(
        self, dataset_id: str, current_schema: DatasetSchema
    ) -> list[SchemaChange]:
        """Detect schema changes between the latest registered version and current.

        Compares column presence, data types, and nullability to identify
        changes. Classifies changes as breaking or non-breaking.

        Args:
            dataset_id: Dataset to check for drift
            current_schema: Current schema snapshot

        Returns:
            List of SchemaChange objects (empty if no changes detected)

        Raises:
            BreakingChangeAlert: If breaking changes are detected (in strict mode)

        Example:
            >>> current = SchemaRegistry.extract_schema_from_dataframe(df, "my-dataset")
            >>> changes = registry.detect_drift("my-dataset", current)
            >>> for change in changes:
            ...     if change.is_breaking:
            ...         print(f"BREAKING: {change.description}")
        """
        previous_schema = self.get_schema_version(dataset_id)
        if previous_schema is None:
            logger.warning(f"No previous schema found for {dataset_id}, skipping drift detection")
            return []

        changes: list[SchemaChange] = []
        previous_cols = previous_schema.columns
        current_cols = current_schema.columns

        # Detect deleted columns (breaking)
        for col_name in previous_cols:
            if col_name not in current_cols:
                change = SchemaChange(
                    change_type=ChangeType.COLUMN_DELETION,
                    field_name=col_name,
                    old_value=previous_cols[col_name].dtype,
                    new_value=None,
                    is_breaking=True,
                    description=f"Column '{col_name}' deleted",
                )
                changes.append(change)

        # Detect added columns (non-breaking)
        for col_name in current_cols:
            if col_name not in previous_cols:
                change = SchemaChange(
                    change_type=ChangeType.COLUMN_ADDITION,
                    field_name=col_name,
                    old_value=None,
                    new_value=current_cols[col_name].dtype,
                    is_breaking=False,
                    description=f"Column '{col_name}' added with type {current_cols[col_name].dtype}",
                )
                changes.append(change)

        # Detect type changes (breaking)
        for col_name in current_cols:
            if col_name in previous_cols:
                old_dtype = previous_cols[col_name].dtype
                new_dtype = current_cols[col_name].dtype
                if old_dtype != new_dtype:
                    change = SchemaChange(
                        change_type=ChangeType.TYPE_CHANGE,
                        field_name=col_name,
                        old_value=old_dtype,
                        new_value=new_dtype,
                        is_breaking=True,
                        description=f"Column '{col_name}' type changed: {old_dtype} → {new_dtype}",
                    )
                    changes.append(change)

        # Detect nullability changes (breaking)
        for col_name in current_cols:
            if col_name in previous_cols:
                old_nullable = previous_cols[col_name].nullable
                new_nullable = current_cols[col_name].nullable
                if old_nullable != new_nullable:
                    change = SchemaChange(
                        change_type=ChangeType.NULL_CONSTRAINT_CHANGE,
                        field_name=col_name,
                        old_value=old_nullable,
                        new_value=new_nullable,
                        is_breaking=True,
                        description=f"Column '{col_name}' nullable: {old_nullable} → {new_nullable}",
                    )
                    changes.append(change)

        if changes:
            logger.warning(f"Schema drift detected for {dataset_id}: {len(changes)} changes")
            self._log_change(
                dataset_id,
                "drift_detected",
                {
                    "change_count": len(changes),
                    "breaking_count": sum(1 for c in changes if c.is_breaking),
                },
            )

        return changes

    def check_schema_compliance(
        self,
        dataset_id: str,
        current_schema: DatasetSchema,
        enforce_breaking: bool = True,
    ) -> tuple[bool, list[SchemaChange]]:
        """Check if current schema complies with registered contract.

        Detects drift and optionally raises exception on breaking changes.

        Args:
            dataset_id: Dataset to validate
            current_schema: Current schema
            enforce_breaking: If True, raise exception on breaking changes

        Returns:
            Tuple of (is_compliant: bool, changes: list[SchemaChange])

        Raises:
            BreakingChangeAlert: If enforce_breaking=True and breaking changes found
        """
        changes = self.detect_drift(dataset_id, current_schema)
        breaking_changes = [c for c in changes if c.is_breaking]

        if breaking_changes and enforce_breaking:
            previous_schema = self.get_schema_version(dataset_id)
            from_version = previous_schema.version if previous_schema else 0
            alert = BreakingChangeAlert(
                dataset_id=dataset_id,
                from_version=from_version,
                to_version=current_schema.version,
                breaking_changes=breaking_changes,
                timestamp=datetime.utcnow(),
                recommendation="Review schema changes and update downstream KPI computations",
            )
            logger.error(str(alert))
            self._log_change(
                dataset_id,
                "breaking_change_alert",
                {"breaking_change_count": len(breaking_changes)},
            )
            raise alert

        return len(breaking_changes) == 0, changes

    def _load_schema_history(self, dataset_id: str) -> list[DatasetSchema]:
        """Load all schema versions for a dataset from storage.

        Args:
            dataset_id: Dataset identifier

        Returns:
            List of DatasetSchema objects, earliest to latest
        """
        history_path = self.storage_dir / f"{dataset_id}_history.json"
        if not history_path.exists():
            return []

        try:
            with open(history_path, "r") as f:
                data = json.load(f)
                return sorted(
                    [DatasetSchema.from_dict(item) for item in data],
                    key=lambda s: s.version,
                )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load schema history for {dataset_id}: {e}")
            return []

    def get_schema_changelog(self, dataset_id: str) -> list[dict[str, Any]]:
        """Get changelog of all schema versions for a dataset.

        Returns a summary of changes between consecutive versions.

        Args:
            dataset_id: Dataset identifier

        Returns:
            List of changelog entries with version numbers and change summaries

        Example:
            >>> changelog = registry.get_schema_changelog("my-dataset")
            >>> for entry in changelog:
            ...     print(f"v{entry['from']} → v{entry['to']}: {entry['changes']}")
        """
        history = self._load_schema_history(dataset_id)
        if len(history) < 2:
            return []

        changelog: list[dict[str, Any]] = []
        for i in range(1, len(history)):
            prev_schema = history[i - 1]
            curr_schema = history[i]
            changes = self.detect_drift(dataset_id, curr_schema)

            changelog.append(
                {
                    "from": prev_schema.version,
                    "to": curr_schema.version,
                    "timestamp": curr_schema.captured_at.isoformat(),
                    "change_count": len(changes),
                    "breaking_count": sum(1 for c in changes if c.is_breaking),
                    "changes": [
                        {
                            "type": c.change_type.value,
                            "field": c.field_name,
                            "description": c.description,
                        }
                        for c in changes
                    ],
                }
            )

        return changelog
