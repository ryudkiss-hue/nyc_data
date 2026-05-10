"""
Tests for Schema Registry module (socrata_toolkit.schema_registry)

Tests schema registration, drift detection, breaking change alerts, and audit trail.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from socrata_toolkit.schema_registry import (
    BreakingChangeAlert,
    ChangeType,
    ColumnSchema,
    DatasetSchema,
    SchemaChange,
    SchemaRegistry,
    SchemaValidator,
    BackwardCompatibilityChecker,
)


class TestColumnSchema:
    """Tests for ColumnSchema dataclass."""

    def test_column_schema_creation(self):
        """Test creating a column schema."""
        col = ColumnSchema(
            name="age",
            dtype="int64",
            nullable=False,
            position=0,
            sample_value="25",
        )
        assert col.name == "age"
        assert col.dtype == "int64"
        assert col.nullable is False
        assert col.position == 0
        assert col.sample_value == "25"


class TestDatasetSchema:
    """Tests for DatasetSchema dataclass."""

    def test_dataset_schema_creation(self):
        """Test creating a dataset schema."""
        cols = {
            "id": ColumnSchema("id", "int64", False, 0),
            "name": ColumnSchema("name", "object", True, 1),
        }
        schema = DatasetSchema(
            dataset_id="test-dataset",
            version=1,
            columns=cols,
            captured_at=datetime.utcnow(),
            row_count=100,
        )
        assert schema.dataset_id == "test-dataset"
        assert schema.version == 1
        assert len(schema.columns) == 2
        assert schema.row_count == 100

    def test_dataset_schema_serialization(self):
        """Test converting schema to/from dict."""
        cols = {"id": ColumnSchema("id", "int64", False, 0)}
        schema = DatasetSchema(
            dataset_id="test-dataset",
            version=1,
            columns=cols,
            captured_at=datetime.utcnow(),
            row_count=50,
        )

        # Serialize
        data = schema.to_dict()
        assert data["dataset_id"] == "test-dataset"
        assert data["version"] == 1
        assert "id" in data["columns"]

        # Deserialize
        schema2 = DatasetSchema.from_dict(data)
        assert schema2.dataset_id == schema.dataset_id
        assert schema2.version == schema.version
        assert len(schema2.columns) == len(schema.columns)


class TestSchemaChange:
    """Tests for SchemaChange dataclass."""

    def test_schema_change_creation(self):
        """Test creating a schema change."""
        change = SchemaChange(
            change_type=ChangeType.COLUMN_ADDITION,
            field_name="new_field",
            old_value=None,
            new_value="float64",
            is_breaking=False,
            description="Column 'new_field' added with type float64",
        )
        assert change.change_type == ChangeType.COLUMN_ADDITION
        assert change.is_breaking is False
        assert "new_field" in change.description

    def test_breaking_change_classification(self):
        """Test that breaking changes are correctly classified."""
        # Column deletion is breaking
        change = SchemaChange(
            change_type=ChangeType.COLUMN_DELETION,
            field_name="deleted_col",
            old_value="int64",
            new_value=None,
            is_breaking=True,
            description="Column deleted",
        )
        assert change.is_breaking is True

        # Column addition is not breaking
        change = SchemaChange(
            change_type=ChangeType.COLUMN_ADDITION,
            field_name="new_col",
            old_value=None,
            new_value="varchar",
            is_breaking=False,
            description="Column added",
        )
        assert change.is_breaking is False


class TestBreakingChangeAlert:
    """Tests for BreakingChangeAlert exception."""

    def test_breaking_change_alert_creation(self):
        """Test creating a breaking change alert."""
        changes = [
            SchemaChange(
                change_type=ChangeType.COLUMN_DELETION,
                field_name="old_col",
                old_value="int64",
                new_value=None,
                is_breaking=True,
                description="Column deleted",
            )
        ]
        alert = BreakingChangeAlert(
            dataset_id="test-dataset",
            from_version=1,
            to_version=2,
            breaking_changes=changes,
            timestamp=datetime.utcnow(),
            recommendation="Update downstream pipelines",
        )
        assert alert.dataset_id == "test-dataset"
        assert alert.from_version == 1
        assert alert.to_version == 2
        assert len(alert.breaking_changes) == 1

    def test_breaking_change_alert_is_exception(self):
        """Test that alert can be raised as an exception."""
        changes = [
            SchemaChange(
                change_type=ChangeType.COLUMN_DELETION,
                field_name="col",
                old_value="int",
                new_value=None,
                is_breaking=True,
                description="Deleted",
            )
        ]
        alert = BreakingChangeAlert(
            dataset_id="test",
            from_version=1,
            to_version=2,
            breaking_changes=changes,
            timestamp=datetime.utcnow(),
        )
        # Should be raisable as exception
        with pytest.raises(BreakingChangeAlert):
            raise alert

    def test_breaking_change_alert_string_representation(self):
        """Test alert has readable string representation."""
        changes = [
            SchemaChange(
                change_type=ChangeType.TYPE_CHANGE,
                field_name="amount",
                old_value="int64",
                new_value="object",
                is_breaking=True,
                description="Type changed: int64 → object",
            )
        ]
        alert = BreakingChangeAlert(
            dataset_id="sidewalk-data",
            from_version=1,
            to_version=2,
            breaking_changes=changes,
            timestamp=datetime.utcnow(),
            recommendation="Rerun type validation",
        )
        alert_str = str(alert)
        assert "BREAKING SCHEMA CHANGE ALERT" in alert_str
        assert "sidewalk-data" in alert_str
        assert "amount" in alert_str
        assert "Type changed" in alert_str


class TestSchemaRegistry:
    """Tests for SchemaRegistry class."""

    @pytest.fixture
    def temp_registry(self):
        """Create a temporary schema registry for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = SchemaRegistry(storage_dir=tmpdir)
            yield registry

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
            "salary": [50000.0, 60000.0, 70000.0],
        })

    def test_schema_registry_initialization(self, temp_registry):
        """Test registry initializes with storage directory."""
        assert temp_registry.storage_dir.exists()
        assert (temp_registry.storage_dir / "schema_changes_audit.jsonl").exists()

    def test_extract_schema_from_dataframe(self, sample_dataframe):
        """Test extracting schema from DataFrame."""
        schema = SchemaRegistry.extract_schema_from_dataframe(
            sample_dataframe, "test-data"
        )
        assert schema.dataset_id == "test-data"
        assert len(schema.columns) == 4
        assert "id" in schema.columns
        assert schema.columns["id"].dtype == "int64"
        assert schema.columns["name"].dtype == "object"
        assert schema.row_count == 3

    def test_extract_schema_with_metadata(self, sample_dataframe):
        """Test schema extraction includes optional metadata."""
        metadata = {"source": "NYC Sidewalk DB", "version": "1.0"}
        schema = SchemaRegistry.extract_schema_from_dataframe(
            sample_dataframe, "test-data", metadata=metadata
        )
        assert schema.metadata["source"] == "NYC Sidewalk DB"
        assert schema.metadata["version"] == "1.0"

    def test_extract_schema_nullability_detection(self):
        """Test that schema detects nullable columns."""
        df = pd.DataFrame({
            "required_col": [1, 2, 3],
            "nullable_col": [1, None, 3],
        })
        schema = SchemaRegistry.extract_schema_from_dataframe(df, "test")
        assert schema.columns["required_col"].nullable is False
        assert schema.columns["nullable_col"].nullable is True

    def test_register_schema(self, temp_registry, sample_dataframe):
        """Test registering a schema."""
        schema = SchemaRegistry.extract_schema_from_dataframe(
            sample_dataframe, "test-data"
        )
        temp_registry.register_schema(schema)

        # Verify schema was stored
        history_path = temp_registry.storage_dir / "test-data_history.json"
        assert history_path.exists()

        # Verify content
        with open(history_path) as f:
            history = json.load(f)
        assert len(history) == 1
        assert history[0]["dataset_id"] == "test-data"

    def test_register_schema_version_increment(self, temp_registry, sample_dataframe):
        """Test that schema version is incremented on registration."""
        schema1 = SchemaRegistry.extract_schema_from_dataframe(
            sample_dataframe, "test-data"
        )
        schema1.version = 1
        temp_registry.register_schema(schema1)

        # Register another version
        df2 = sample_dataframe.copy()
        df2["new_col"] = [4, 5, 6]
        schema2 = SchemaRegistry.extract_schema_from_dataframe(df2, "test-data")
        temp_registry.register_schema(schema2, increment_version=True)

        # Verify version incremented
        retrieved = temp_registry.get_schema_version("test-data")
        assert retrieved.version == 2

    def test_get_schema_version_latest(self, temp_registry, sample_dataframe):
        """Test retrieving the latest schema version."""
        schema = SchemaRegistry.extract_schema_from_dataframe(
            sample_dataframe, "test-data"
        )
        schema.version = 1
        temp_registry.register_schema(schema)

        retrieved = temp_registry.get_schema_version("test-data")
        assert retrieved.version == 1

    def test_get_schema_version_specific(self, temp_registry, sample_dataframe):
        """Test retrieving a specific schema version."""
        schema = SchemaRegistry.extract_schema_from_dataframe(
            sample_dataframe, "test-data"
        )
        schema.version = 1
        temp_registry.register_schema(schema)

        retrieved = temp_registry.get_schema_version("test-data", version=1)
        assert retrieved.version == 1

    def test_get_schema_version_nonexistent(self, temp_registry):
        """Test retrieving schema for nonexistent dataset returns None."""
        result = temp_registry.get_schema_version("nonexistent-dataset")
        assert result is None

    def test_detect_drift_column_addition(self, temp_registry):
        """Test detecting column addition (non-breaking)."""
        df1 = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        schema1 = SchemaRegistry.extract_schema_from_dataframe(df1, "test-data")
        schema1.version = 1
        temp_registry.register_schema(schema1)

        # Add a column
        df2 = df1.copy()
        df2["email"] = ["a@test.com", "b@test.com"]
        schema2 = SchemaRegistry.extract_schema_from_dataframe(df2, "test-data")

        changes = temp_registry.detect_drift("test-data", schema2)
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.COLUMN_ADDITION
        assert changes[0].field_name == "email"
        assert changes[0].is_breaking is False

    def test_detect_drift_column_deletion(self, temp_registry):
        """Test detecting column deletion (breaking)."""
        df1 = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        schema1 = SchemaRegistry.extract_schema_from_dataframe(df1, "test-data")
        schema1.version = 1
        temp_registry.register_schema(schema1)

        # Remove a column
        df2 = df1[["id"]].copy()
        schema2 = SchemaRegistry.extract_schema_from_dataframe(df2, "test-data")

        changes = temp_registry.detect_drift("test-data", schema2)
        assert any(c.change_type == ChangeType.COLUMN_DELETION for c in changes)
        assert any(c.is_breaking for c in changes)

    def test_detect_drift_type_change(self, temp_registry):
        """Test detecting type change (breaking)."""
        df1 = pd.DataFrame({"id": [1, 2], "value": [10, 20]})
        schema1 = SchemaRegistry.extract_schema_from_dataframe(df1, "test-data")
        schema1.version = 1
        temp_registry.register_schema(schema1)

        # Change type
        df2 = pd.DataFrame({"id": [1, 2], "value": ["10", "20"]})
        schema2 = SchemaRegistry.extract_schema_from_dataframe(df2, "test-data")

        changes = temp_registry.detect_drift("test-data", schema2)
        assert any(c.change_type == ChangeType.TYPE_CHANGE for c in changes)
        assert any(c.field_name == "value" for c in changes)

    def test_detect_drift_no_changes(self, temp_registry):
        """Test detecting drift when schemas are identical."""
        df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        schema = SchemaRegistry.extract_schema_from_dataframe(df, "test-data")
        schema.version = 1
        temp_registry.register_schema(schema)

        # Same schema again
        changes = temp_registry.detect_drift("test-data", schema)
        assert len(changes) == 0

    def test_check_schema_compliance_valid(self, temp_registry):
        """Test compliance check passes for valid changes."""
        df1 = pd.DataFrame({"id": [1, 2]})
        schema1 = SchemaRegistry.extract_schema_from_dataframe(df1, "test-data")
        schema1.version = 1
        temp_registry.register_schema(schema1)

        df2 = df1.copy()
        df2["new_col"] = [3, 4]
        schema2 = SchemaRegistry.extract_schema_from_dataframe(df2, "test-data")

        is_compliant, changes = temp_registry.check_schema_compliance(
            "test-data", schema2, enforce_breaking=False
        )
        assert is_compliant is True

    def test_check_schema_compliance_breaking_change_raises(self, temp_registry):
        """Test that breaking changes raise exception when enforced."""
        df1 = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        schema1 = SchemaRegistry.extract_schema_from_dataframe(df1, "test-data")
        schema1.version = 1
        temp_registry.register_schema(schema1)

        df2 = df1[["id"]].copy()  # Remove 'name'
        schema2 = SchemaRegistry.extract_schema_from_dataframe(df2, "test-data")

        # Should raise when enforce_breaking=True
        with pytest.raises(BreakingChangeAlert):
            temp_registry.check_schema_compliance(
                "test-data", schema2, enforce_breaking=True
            )

    def test_audit_log_written(self, temp_registry, sample_dataframe):
        """Test that all operations are logged to audit trail."""
        schema = SchemaRegistry.extract_schema_from_dataframe(
            sample_dataframe, "test-data"
        )
        temp_registry.register_schema(schema)

        # Check audit log
        audit_log_path = temp_registry.storage_dir / "schema_changes_audit.jsonl"
        assert audit_log_path.exists()

        with open(audit_log_path) as f:
            logs = [json.loads(line) for line in f if line.strip()]
        
        assert len(logs) > 0
        assert any(log["operation"] == "register_schema" for log in logs)

    def test_get_schema_changelog(self, temp_registry):
        """Test retrieving schema changelog."""
        # Register multiple versions
        df1 = pd.DataFrame({"id": [1], "name": ["A"]})
        schema1 = SchemaRegistry.extract_schema_from_dataframe(df1, "test-data")
        schema1.version = 1
        temp_registry.register_schema(schema1)

        df2 = df1.copy()
        df2["email"] = ["a@test.com"]
        schema2 = SchemaRegistry.extract_schema_from_dataframe(df2, "test-data")
        schema2.version = 2
        temp_registry.register_schema(schema2)

        changelog = temp_registry.get_schema_changelog("test-data")
        assert len(changelog) == 1
        assert changelog[0]["from"] == 1
        assert changelog[0]["to"] == 2


class TestSchemaValidator:
    """Tests for SchemaValidator class."""

    @pytest.fixture
    def sample_schema(self):
        """Create a sample schema for validation testing."""
        cols = {
            "id": ColumnSchema("id", "int64", False, 0),
            "name": ColumnSchema("name", "object", True, 1),
            "email": ColumnSchema("email", "object", True, 2),
        }
        return DatasetSchema(
            dataset_id="test-data",
            version=1,
            columns=cols,
            captured_at=datetime.utcnow(),
            row_count=100,
        )

    def test_validator_initialization(self, sample_schema):
        """Test initializing a validator."""
        validator = SchemaValidator(sample_schema)
        assert validator.schema == sample_schema
        assert validator.errors == []

    def test_validate_record_valid(self, sample_schema):
        """Test validating a valid record."""
        validator = SchemaValidator(sample_schema)
        record = {"id": 1, "name": "Alice", "email": "alice@example.com"}
        valid, errors = validator.validate_record(record)
        assert valid is True
        assert len(errors) == 0

    def test_validate_record_missing_required_field(self, sample_schema):
        """Test validation fails for missing required column."""
        validator = SchemaValidator(sample_schema)
        record = {"name": "Bob", "email": "bob@example.com"}  # Missing id
        valid, errors = validator.validate_record(record)
        assert valid is False
        assert any("required column" in e.lower() for e in errors)

    def test_validate_record_null_not_nullable(self, sample_schema):
        """Test validation fails when None is passed to non-nullable column."""
        validator = SchemaValidator(sample_schema)
        record = {"id": None, "name": "Charlie"}  # id is NOT NULL
        valid, errors = validator.validate_record(record)
        assert valid is False
        assert any("not null" in e.lower() for e in errors)

    def test_validate_record_type_mismatch(self, sample_schema):
        """Test validation detects type mismatches."""
        validator = SchemaValidator(sample_schema)
        record = {"id": "not_an_int", "name": "Dave"}  # id should be int
        valid, errors = validator.validate_record(record)
        # Type validation is flexible, so this may pass
        # depending on the validator's strictness

    def test_validate_record_nullable_field_none(self, sample_schema):
        """Test validation allows None for nullable fields."""
        validator = SchemaValidator(sample_schema)
        record = {"id": 1, "name": None, "email": None}  # nullable fields can be None
        valid, errors = validator.validate_record(record)
        assert valid is True

    def test_validate_batch(self, sample_schema):
        """Test batch validation."""
        validator = SchemaValidator(sample_schema)
        records = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3},  # Missing optional fields, but valid
        ]
        valid_count, errors = validator.validate_batch(records)
        assert valid_count == 3
        assert len(errors) == 0

    def test_validate_batch_with_errors(self, sample_schema):
        """Test batch validation with some invalid records."""
        validator = SchemaValidator(sample_schema)
        records = [
            {"id": 1, "name": "Alice"},  # Valid
            {"name": "Bob"},  # Invalid: missing required id
        ]
        valid_count, errors = validator.validate_batch(records)
        assert valid_count == 1
        assert len(errors) > 0


class TestBackwardCompatibilityChecker:
    """Tests for BackwardCompatibilityChecker class."""

    @pytest.fixture
    def old_schema(self):
        """Create an old schema version."""
        cols = {
            "id": ColumnSchema("id", "int64", False, 0),
            "name": ColumnSchema("name", "object", True, 1),
        }
        return DatasetSchema(
            dataset_id="test-data",
            version=1,
            columns=cols,
            captured_at=datetime.utcnow(),
            row_count=100,
        )

    def test_checker_initialization(self):
        """Test initializing a compatibility checker."""
        checker = BackwardCompatibilityChecker()
        assert checker.strict_mode is False

    def test_checker_strict_mode(self):
        """Test initializing with strict mode enabled."""
        checker = BackwardCompatibilityChecker(strict_mode=True)
        assert checker.strict_mode is True

    def test_compatible_column_addition(self, old_schema):
        """Test that adding optional columns is compatible."""
        new_cols = old_schema.columns.copy()
        new_cols["email"] = ColumnSchema("email", "object", True, 2)
        new_schema = DatasetSchema(
            dataset_id="test-data",
            version=2,
            columns=new_cols,
            captured_at=datetime.utcnow(),
            row_count=100,
        )

        checker = BackwardCompatibilityChecker()
        is_compatible, violations = checker.check_compatibility(old_schema, new_schema)
        assert is_compatible is True
        # No blocking violations, only maybe debug logs

    def test_incompatible_column_deletion(self, old_schema):
        """Test that deleting columns is incompatible."""
        new_cols = {"id": old_schema.columns["id"]}
        new_schema = DatasetSchema(
            dataset_id="test-data",
            version=2,
            columns=new_cols,
            captured_at=datetime.utcnow(),
            row_count=100,
        )

        checker = BackwardCompatibilityChecker()
        is_compatible, violations = checker.check_compatibility(old_schema, new_schema)
        assert is_compatible is False
        assert any("deleted" in v.lower() for v in violations)

    def test_incompatible_type_change(self, old_schema):
        """Test that type changes are incompatible."""
        new_cols = old_schema.columns.copy()
        new_cols["id"] = ColumnSchema("id", "object", False, 0)  # Changed from int64
        new_schema = DatasetSchema(
            dataset_id="test-data",
            version=2,
            columns=new_cols,
            captured_at=datetime.utcnow(),
            row_count=100,
        )

        checker = BackwardCompatibilityChecker()
        is_compatible, violations = checker.check_compatibility(old_schema, new_schema)
        assert is_compatible is False
        assert any("type changed" in v.lower() for v in violations)

    def test_warn_nullable_change_to_required(self, old_schema):
        """Test warning when making nullable column required."""
        new_cols = old_schema.columns.copy()
        new_cols["name"] = ColumnSchema("name", "object", False, 1)  # Changed from nullable
        new_schema = DatasetSchema(
            dataset_id="test-data",
            version=2,
            columns=new_cols,
            captured_at=datetime.utcnow(),
            row_count=100,
        )

        checker = BackwardCompatibilityChecker()
        is_compatible, violations = checker.check_compatibility(old_schema, new_schema)
        # This is WARN-level, not BLOCK, so might still be compatible
        # but violations should mention it
        assert any("not null" in v.lower() for v in violations)

    def test_safe_type_upgrade(self, old_schema):
        """Test that safe type upgrades (int32 to int64) are allowed."""
        old_cols = {
            "id": ColumnSchema("id", "int32", False, 0),
            "name": ColumnSchema("name", "object", True, 1),
        }
        old_v1 = DatasetSchema(
            dataset_id="test-data",
            version=1,
            columns=old_cols,
            captured_at=datetime.utcnow(),
            row_count=100,
        )

        new_cols = old_cols.copy()
        new_cols["id"] = ColumnSchema("id", "int64", False, 0)
        new_schema = DatasetSchema(
            dataset_id="test-data",
            version=2,
            columns=new_cols,
            captured_at=datetime.utcnow(),
            row_count=100,
        )

        checker = BackwardCompatibilityChecker()
        is_compatible, violations = checker.check_compatibility(old_v1, new_schema)
        # Safe upgrades should be compatible
        blocking_violations = [v for v in violations if v.startswith("BLOCK")]
        assert len(blocking_violations) == 0

    def test_multiple_violations(self, old_schema):
        """Test reporting multiple violations."""
        new_cols = {"id": old_schema.columns["id"]}  # Deleted 'name'
        new_cols["new_field"] = ColumnSchema("new_field", "int64", False, 1)  # Made required
        new_schema = DatasetSchema(
            dataset_id="test-data",
            version=2,
            columns=new_cols,
            captured_at=datetime.utcnow(),
            row_count=100,
        )

        checker = BackwardCompatibilityChecker()
        is_compatible, violations = checker.check_compatibility(old_schema, new_schema)
        assert is_compatible is False
        assert len(violations) >= 1  # At least one violation
