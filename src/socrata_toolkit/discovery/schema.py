"""
Schema Registry Module - NYC DOT Sidewalk Toolkit

Purpose: Track schema versions, detect drift, enforce contracts on ingested datasets.
This module maintains version history, detects schema changes, and alerts data engineers
to breaking changes that could impact downstream transformations and KPI computations.

Supports both JSON file storage (local development) and PostgreSQL persistence (production).
Enforces backward compatibility rules and provides schema validation.

Standards: Python 3.9+, type hints, comprehensive docstrings, audit trail logging
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Type compatibility matrix for schema evolution
# Maps from dtype to compatible upgrade dtypes
TYPE_COMPATIBILITY = {
    "int32": {"int32", "int64", "float64", "object"},
    "int64": {"int64", "float64", "object"},
    "float32": {"float32", "float64", "object"},
    "float64": {"float64", "object"},
    "bool": {"bool", "int32", "int64", "object"},
    "object": {"object"},
    "string": {"string", "object"},
    "datetime64[ns]": {"datetime64[ns]", "object"},
}


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
    sample_value: str | None = None


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


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle NumPy types."""
    def default(self, obj: Any) -> Any:
        if hasattr(obj, "tolist"):
            return obj.tolist()
        if hasattr(obj, "item"):
            try:
                return obj.item()
            except Exception:
                pass
        if isinstance(obj, (datetime)):
             return obj.isoformat()
        return super().default(obj)


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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset_id": dataset_id,
            "operation": operation,
            **details,
        }
        with open(self.audit_log_path, "a") as f:
            f.write(json.dumps(log_entry, cls=NumpyEncoder) + "\n")
        logger.info(f"Schema audit logged: {dataset_id} {operation}")

    @staticmethod
    def extract_schema_from_dataframe(
        df: pd.DataFrame, dataset_id: str, metadata: dict[str, Any] | None = None
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

            dtype = str(col_data.dtype)
            if dtype == "string":
                dtype = "object"
            elif "str" in dtype.lower():
                dtype = "object"

            columns[col_name] = ColumnSchema(
                name=col_name,
                dtype=dtype,
                nullable=bool(nullable),
                position=position,
                sample_value=sample_value,
            )

        metadata = metadata or {}
        return DatasetSchema(
            dataset_id=dataset_id,
            version=1,
            columns=columns,
            captured_at=datetime.now(timezone.utc),
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
            json.dump(all_versions, f, indent=2, cls=NumpyEncoder)

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
        self, dataset_id: str, version: int | None = None
    ) -> DatasetSchema | None:
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
                timestamp=datetime.now(timezone.utc),
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
            with open(history_path) as f:
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


class SchemaValidator:
    """Validates data records against a schema definition.
    
    Provides type checking, nullability validation, and detailed error reporting
    for records that violate schema constraints.
    
    Usage:
        schema = registry.get_schema_version("my-dataset")
        validator = SchemaValidator(schema)
        report = validator.validate_record({"id": 1, "name": "John"})
        if not report.valid:
            print(report.errors)
    """
    
    def __init__(self, schema: DatasetSchema):
        """Initialize validator with a schema.
        
        Args:
            schema: DatasetSchema to validate against
        """
        self.schema = schema
        self.errors: list[str] = []
        self.warnings: list[str] = []
    
    def validate_record(self, record: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a single record against the schema.
        
        Args:
            record: Dictionary record to validate
            
        Returns:
            Tuple of (is_valid: bool, error_messages: list[str])
            
        Example:
            >>> validator = SchemaValidator(schema)
            >>> valid, errors = validator.validate_record({"id": 1, "name": "Alice"})
            >>> if not valid:
            ...     print(f"Validation failed: {errors}")
        """
        errors = []
        
        # Check for missing required fields (non-nullable columns)
        for col_name, col_schema in self.schema.columns.items():
            if col_name not in record:
                if not col_schema.nullable:
                    errors.append(f"Missing required column: '{col_name}'")
            elif record[col_name] is None and not col_schema.nullable:
                errors.append(f"Column '{col_name}' is NOT NULL but received None")
        
        # Check for unexpected columns
        schema_cols = set(self.schema.columns.keys())
        record_cols = set(record.keys())
        extra_cols = record_cols - schema_cols
        if extra_cols:
            logger.warning(f"Record has unexpected columns: {extra_cols}")
        
        # Type validation
        for col_name, value in record.items():
            if col_name not in self.schema.columns:
                continue
            if value is None:
                continue
                
            col_schema = self.schema.columns[col_name]
            expected_type = col_schema.dtype
            actual_type = self._infer_type(value)
            
            if not self._is_type_compatible(actual_type, expected_type):
                errors.append(
                    f"Column '{col_name}': type mismatch. "
                    f"Expected {expected_type}, got {actual_type}"
                )
        
        return len(errors) == 0, errors
    
    def validate_batch(self, records: list[dict[str, Any]]) -> tuple[int, list[str]]:
        """Validate a batch of records.
        
        Args:
            records: List of records to validate
            
        Returns:
            Tuple of (valid_count: int, error_messages: list[str])
        """
        valid_count = 0
        all_errors = []
        
        for idx, record in enumerate(records):
            valid, errors = self.validate_record(record)
            if valid:
                valid_count += 1
            else:
                for error in errors:
                    all_errors.append(f"Record {idx}: {error}")
        
        return valid_count, all_errors
    
    @staticmethod
    def _infer_type(value: Any) -> str:
        """Infer pandas/numpy dtype from Python value.
        
        Args:
            value: Python value to infer type from
            
        Returns:
            String representation of dtype
        """
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int64"
        elif isinstance(value, float):
            return "float64"
        elif isinstance(value, str):
            return "object"
        elif isinstance(value, (list, dict)):
            return "object"
        else:
            return "object"
    
    @staticmethod
    def _is_type_compatible(actual: str, expected: str) -> bool:
        """Check if actual type is compatible with expected type.
        
        Args:
            actual: Inferred type from value
            expected: Expected type from schema
            
        Returns:
            True if types are compatible
        """
        # Allow flexible type coercion
        if expected == "object":
            return True
        if actual == expected:
            return True
        
        # String and object are often interchangeable
        if expected in ("object", "string") and actual in ("object", "string"):
            return True
        
        # Numeric types can be coerced upward
        if expected in ("float64", "int64") and actual in ("int64", "int32", "float64", "float32"):
            return True
        
        return False


class BackwardCompatibilityChecker:
    """Enforces backward compatibility rules during schema evolution.
    
    Implements rules per the NYC DOT data governance standards:
    - ALLOW: Adding optional columns, adding columns with default values
    - WARN: Renaming columns, making columns optional when previously required
    - BLOCK: Removing columns, changing column types, making columns required
    
    Usage:
        checker = BackwardCompatibilityChecker()
        is_compatible, violations = checker.check_compatibility(old_schema, new_schema)
    """
    
    def __init__(self, strict_mode: bool = False):
        """Initialize the compatibility checker.
        
        Args:
            strict_mode: If True, warn about all non-addition changes
        """
        self.strict_mode = strict_mode
    
    def check_compatibility(
        self, 
        old_schema: DatasetSchema, 
        new_schema: DatasetSchema
    ) -> tuple[bool, list[str]]:
        """Check if new schema is backward compatible with old schema.
        
        Args:
            old_schema: Previously registered schema version
            new_schema: Candidate schema version
            
        Returns:
            Tuple of (is_compatible: bool, violation_messages: list[str])
            
        Example:
            >>> checker = BackwardCompatibilityChecker()
            >>> compatible, violations = checker.check_compatibility(v1_schema, v2_schema)
            >>> if not compatible:
            ...     print(f"Incompatible: {violations}")
        """
        violations = []
        old_cols = old_schema.columns
        new_cols = new_schema.columns
        
        # Rule 1: BLOCK - Column deletion
        for col_name in old_cols:
            if col_name not in new_cols:
                violations.append(f"BLOCK: Column '{col_name}' was deleted (breaking change)")
        
        # Rule 2: BLOCK - Type changes (unless explicit casting rule provided)
        for col_name in old_cols:
            if col_name in new_cols:
                old_dtype = old_cols[col_name].dtype
                new_dtype = new_cols[col_name].dtype
                
                if old_dtype != new_dtype:
                    if not self._is_type_upgrade_safe(old_dtype, new_dtype):
                        violations.append(
                            f"BLOCK: Column '{col_name}' type changed: "
                            f"{old_dtype} → {new_dtype} (breaking change)"
                        )
        
        # Rule 3: WARN - Making previously optional column required
        for col_name in old_cols:
            if col_name in new_cols:
                old_nullable = old_cols[col_name].nullable
                new_nullable = new_cols[col_name].nullable
                
                if old_nullable and not new_nullable:
                    violations.append(
                        f"WARN: Column '{col_name}' made NOT NULL "
                        f"(may break existing pipelines)"
                    )
        
        # Rule 4: ALLOW - Adding new optional columns
        for col_name in new_cols:
            if col_name not in old_cols and new_cols[col_name].nullable:
                logger.debug(f"ALLOW: New optional column '{col_name}' added")
        
        # Rule 5: WARN - Renaming (detected by column position changes with type matches)
        if self.strict_mode:
            potential_renames = self._detect_potential_renames(old_cols, new_cols)
            for old_name, new_name in potential_renames:
                violations.append(
                    f"WARN: Column '{old_name}' may have been renamed to '{new_name}' "
                    f"(strict mode warning)"
                )
        
        # Determine overall compatibility
        blocking_violations = [v for v in violations if v.startswith("BLOCK")]
        is_compatible = len(blocking_violations) == 0
        
        return is_compatible, violations
    
    @staticmethod
    def _is_type_upgrade_safe(old_dtype: str, new_dtype: str) -> bool:
        """Check if type change is a safe upgrade (widening, not narrowing).
        
        Args:
            old_dtype: Original column dtype
            new_dtype: New column dtype
            
        Returns:
            True if change is a safe upgrade
        """
        # int32 → int64, float32 → float64 are safe upgrades
        safe_upgrades = {
            ("int32", "int64"),
            ("int32", "float64"),
            ("int64", "float64"),
            ("float32", "float64"),
            ("bool", "int64"),
            ("bool", "object"),
        }
        
        return (old_dtype, new_dtype) in safe_upgrades or old_dtype == new_dtype
    
    @staticmethod
    def _detect_potential_renames(
        old_cols: dict[str, ColumnSchema],
        new_cols: dict[str, ColumnSchema]
    ) -> list[tuple[str, str]]:
        """Detect columns that may have been renamed.
        
        Heuristic: same dtype and position suggests rename.
        
        Args:
            old_cols: Previous column definitions
            new_cols: Current column definitions
            
        Returns:
            List of (old_name, new_name) tuples for potential renames
        """
        renames = []
        old_by_type_pos = {
            (col.dtype, col.position): name 
            for name, col in old_cols.items()
        }
        
        for new_name, new_col in new_cols.items():
            key = (new_col.dtype, new_col.position)
            if key in old_by_type_pos:
                old_name = old_by_type_pos[key]
                if old_name != new_name and old_name not in new_cols:
                    renames.append((old_name, new_name))
        
        return renames
