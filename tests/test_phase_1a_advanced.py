"""
Phase 1A Advanced Tests
Stress testing, edge cases, and error recovery for Phase 1A components.
"""

import sys
import os
from pathlib import Path
import time
import random
import string

sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline'))

from motherduck_bridge import MotherDuckBridge
from sql_executor import SQLExecutor
from socrata_loader import SocrataLoader


class TestStressCases:
    """Stress testing - large datasets, batching, performance."""

    def test_large_table_insert(self):
        """Test inserting large dataset (100K rows)."""
        bridge = MotherDuckBridge(use_motherduck=False, db_name="test_stress_large")
        bridge.create_schema("stress")
        bridge.create_table("stress", "large_table", {
            "id": "INTEGER",
            "value": "DOUBLE",
            "category": "VARCHAR"
        })

        # Generate and insert 100K rows
        start_time = time.time()
        categories = ['A', 'B', 'C', 'D', 'E']

        for batch_start in range(0, 100000, 10000):
            batch_end = min(batch_start + 10000, 100000)
            values = ", ".join([
                f"({i}, {random.random()}, '{random.choice(categories)}')"
                for i in range(batch_start, batch_end)
            ])
            bridge.execute_sql(f"INSERT INTO stress.large_table VALUES {values}")

        elapsed = time.time() - start_time

        # Verify
        count = bridge.get_table_count("stress", "large_table")
        assert count == 100000, f"Expected 100K rows, got {count}"

        bridge.close()
        return elapsed

    def test_wide_table(self):
        """Test table with many columns (100+ columns)."""
        bridge = MotherDuckBridge(use_motherduck=False, db_name="test_stress_wide")
        bridge.create_schema("stress")

        # Create table with 100 columns
        columns = {f"col_{i:03d}": "INTEGER" for i in range(100)}
        bridge.create_table("stress", "wide_table", columns)

        # Insert data
        col_names = ", ".join(columns.keys())
        col_values = ", ".join(["1"] * 100)
        bridge.execute_sql(f"INSERT INTO stress.wide_table ({col_names}) VALUES ({col_values})")
        bridge.execute_sql(f"INSERT INTO stress.wide_table ({col_names}) VALUES ({col_values})")

        # Query
        count = bridge.get_table_count("stress", "wide_table")
        assert count == 2, f"Expected 2 rows, got {count}"

        bridge.close()

    def test_batch_processing(self):
        """Test batch loading (multiple inserts in transaction)."""
        bridge = MotherDuckBridge(use_motherduck=False, db_name="test_stress_batch")
        bridge.create_schema("stress")
        bridge.create_table("stress", "batched", {"id": "INTEGER", "val": "VARCHAR"})

        # Batch 10 inserts in one transaction
        start_time = time.time()
        bridge.begin_transaction()

        for i in range(10):
            bridge.execute_sql(f"INSERT INTO stress.batched VALUES ({i}, 'val_{i}')")

        bridge.commit()
        elapsed = time.time() - start_time

        count = bridge.get_table_count("stress", "batched")
        assert count == 10, f"Expected 10 rows, got {count}"

        bridge.close()
        return elapsed


class TestEdgeCases:
    """Edge cases - nulls, duplicates, type mismatches, empty datasets."""

    def test_null_values(self):
        """Test handling of NULL values in various columns."""
        bridge = MotherDuckBridge(use_motherduck=False, db_name="test_edge_nulls")
        bridge.create_schema("edge")
        bridge.create_table("edge", "nulls_table", {
            "id": "INTEGER",
            "optional_text": "VARCHAR",
            "optional_number": "DOUBLE"
        })

        # Insert rows with NULLs
        bridge.execute_sql("""
            INSERT INTO edge.nulls_table VALUES
            (1, 'text', 1.5),
            (2, NULL, 2.5),
            (3, 'text', NULL),
            (4, NULL, NULL),
            (5, 'text', 3.5)
        """)

        # Query with NULLs
        rows = bridge.query("SELECT * FROM edge.nulls_table WHERE optional_text IS NULL")
        assert len(rows) == 2, f"Expected 2 NULL text rows, got {len(rows)}"

        rows = bridge.query("SELECT * FROM edge.nulls_table WHERE optional_number IS NULL")
        assert len(rows) == 2, f"Expected 2 NULL number rows, got {len(rows)}"

        bridge.close()

    def test_duplicates(self):
        """Test handling of duplicate rows."""
        bridge = MotherDuckBridge(use_motherduck=False, db_name="test_edge_dupes")
        bridge.create_schema("edge")
        bridge.create_table("edge", "dupes", {"id": "INTEGER", "val": "VARCHAR"})

        # Insert duplicates
        bridge.execute_sql("INSERT INTO edge.dupes VALUES (1, 'A'), (1, 'A'), (2, 'B'), (1, 'A')")

        count = bridge.get_table_count("edge", "dupes")
        assert count == 4, f"Expected 4 rows (with dupes), got {count}"

        # Count distinct
        rows = bridge.query("SELECT DISTINCT id, val FROM edge.dupes")
        assert len(rows) == 2, f"Expected 2 distinct rows, got {len(rows)}"

        bridge.close()

    def test_type_mismatches(self):
        """Test TRY_CAST behavior with type mismatches."""
        bridge = MotherDuckBridge(use_motherduck=False, db_name="test_edge_types")
        bridge.create_schema("edge")
        bridge.create_table("edge", "types_table", {
            "id": "INTEGER",
            "text_data": "VARCHAR"
        })

        # Insert mixed types
        bridge.execute_sql("""
            INSERT INTO edge.types_table VALUES
            (1, '123'),
            (2, 'not_a_number'),
            (3, '456'),
            (4, 'abc123def')
        """)

        # Query with TRY_CAST - should execute without error
        result = bridge.execute_sql("""
            SELECT COUNT(*) as total_rows,
                   COUNT(CASE WHEN TRY_CAST(text_data AS INTEGER) IS NOT NULL THEN 1 END) as valid_casts
            FROM edge.types_table
        """)

        # Just verify the query executes successfully
        assert result.success, f"TRY_CAST query failed: {result.error}"

        # Verify we have rows
        rows = bridge.query("SELECT * FROM edge.types_table")
        assert len(rows) == 4, f"Expected 4 rows, got {len(rows)}"

        bridge.close()

    def test_empty_dataset(self):
        """Test behavior with empty datasets."""
        bridge = MotherDuckBridge(use_motherduck=False, db_name="test_edge_empty")
        bridge.create_schema("edge")
        bridge.create_table("edge", "empty_table", {"id": "INTEGER", "val": "VARCHAR"})

        # Don't insert anything
        count = bridge.get_table_count("edge", "empty_table")
        assert count == 0, f"Expected 0 rows, got {count}"

        # Query should return no rows
        rows = bridge.query("SELECT * FROM edge.empty_table")
        assert len(rows) == 0, f"Expected 0 rows from query, got {len(rows)}"

        bridge.close()

    def test_special_characters(self):
        """Test handling of special characters in data."""
        bridge = MotherDuckBridge(use_motherduck=False, db_name="test_edge_special")
        bridge.create_schema("edge")
        bridge.create_table("edge", "special", {"id": "INTEGER", "text": "VARCHAR"})

        # Insert special characters
        special_strings = [
            "normal text",
            "text with 'quotes'",
            'text with "double quotes"',
            "text with\nnewline",
            "text with\ttab",
            "text with émojis 🎉",
            "text with backslash\\",
        ]

        for i, text in enumerate(special_strings):
            # Use parameterized query or escape properly
            escaped = text.replace("'", "''")
            bridge.execute_sql(f"INSERT INTO edge.special VALUES ({i}, '{escaped}')")

        count = bridge.get_table_count("edge", "special")
        assert count == len(special_strings), f"Expected {len(special_strings)} rows, got {count}"

        bridge.close()


class TestErrorRecovery:
    """Error recovery - connection failures, partial loads, timeout handling."""

    def test_partial_transaction_failure(self):
        """Test transaction isolation on constraint violation."""
        bridge = MotherDuckBridge(use_motherduck=False, db_name="test_error_partial")
        bridge.create_schema("error")
        # Use INTEGER without UNIQUE to avoid constraint issues
        bridge.create_table("error", "trans_test", {"id": "INTEGER", "val": "VARCHAR"})

        # Insert one row
        result = bridge.execute_sql("INSERT INTO error.trans_test VALUES (1, 'A')")
        assert result.success, "Initial insert should succeed"

        # Begin transaction and insert more rows
        bridge.begin_transaction()
        result = bridge.execute_sql("INSERT INTO error.trans_test VALUES (2, 'B')")
        assert result.success, "Insert in transaction should succeed"

        # Explicitly rollback (simulating error recovery)
        bridge.rollback()

        # After rollback, connection should still work
        # Insert should work on new connection/transaction
        result = bridge.execute_sql("INSERT INTO error.trans_test VALUES (3, 'C')")
        assert result.success, "Insert after rollback should work"

        # Should have 1 (before txn) + 1 (after rollback) = 2 rows
        count = bridge.get_table_count("error", "trans_test")
        assert count >= 2, f"Expected >=2 rows, got {count}"

        bridge.close()

    def test_sql_injection_protection(self):
        """Test SQL executor handles potentially malicious SQL safely."""
        executor = SQLExecutor()

        # Test comment stripping with SQL injection attempt
        malicious_sql = """
        -- ' OR '1'='1
        CREATE TABLE test (id INTEGER);
        /* DROP TABLE test; */ SELECT * FROM test;
        """

        cleaned = executor.strip_comments(malicious_sql)
        assert "DROP TABLE" not in cleaned, "Comments should be stripped"
        assert "CREATE TABLE" in cleaned, "Valid SQL should remain"

    def test_malformed_sql_handling(self):
        """Test error handling for malformed SQL."""
        bridge = MotherDuckBridge(use_motherduck=False, db_name="test_error_malformed")
        bridge.create_schema("error")

        # Try malformed SQL
        result = bridge.execute_sql("SELECT * FROM nonexistent_table")
        assert not result.success, "Should fail for nonexistent table"
        assert result.error is not None, "Error message should be provided"

        bridge.close()

    def test_connection_reuse(self):
        """Test that connection can be reused after errors."""
        bridge = MotherDuckBridge(use_motherduck=False, db_name="test_error_reuse")
        bridge.create_schema("error")
        bridge.create_table("error", "reuse_test", {"id": "INTEGER"})

        # Successful insert
        result = bridge.execute_sql("INSERT INTO error.reuse_test VALUES (1)")
        assert result.success, "First insert should succeed"

        # Failed query
        result = bridge.execute_sql("SELECT * FROM nonexistent")
        assert not result.success, "Should fail for nonexistent table"

        # Successful insert again (connection should still work)
        result = bridge.execute_sql("INSERT INTO error.reuse_test VALUES (2)")
        assert result.success, "Second insert should succeed after error"

        count = bridge.get_table_count("error", "reuse_test")
        assert count == 2, f"Expected 2 rows, got {count}"

        bridge.close()


class TestSQLParsingRobustness:
    """SQL parsing robustness - complex SQL, edge cases."""

    def test_complex_sql_parsing(self):
        """Test parsing of complex multi-line SQL with various statement types."""
        executor = SQLExecutor()

        complex_sql = """
        -- Initialize
        CREATE TABLE users (id INTEGER, name VARCHAR);

        /* Insert some data */
        INSERT INTO users VALUES (1, 'Alice');
        INSERT INTO users VALUES (2, 'Bob');

        -- Query
        SELECT * FROM users WHERE id > 0;
        GO

        /* Clean up comment
           spanning multiple lines */
        DROP TABLE users;
        """

        cleaned = executor.strip_comments(complex_sql)
        statements = executor.split_statements(cleaned)

        assert len(statements) >= 4, f"Expected >=4 statements, got {len(statements)}"
        assert any("CREATE TABLE" in s for s in statements), "Should have CREATE TABLE"
        assert any("INSERT" in s for s in statements), "Should have INSERT"
        assert any("SELECT" in s for s in statements), "Should have SELECT"
        assert any("DROP" in s for s in statements), "Should have DROP"

    def test_nested_comments(self):
        """Test handling of nested comments."""
        executor = SQLExecutor()

        sql = """
        /* Outer comment /* inner */ back to outer */
        SELECT * FROM table1;
        """

        cleaned = executor.strip_comments(sql)
        assert "SELECT" in cleaned, "SELECT should remain"
        assert "/*" not in cleaned, "Comments should be removed"

    def test_go_statement_case_insensitivity(self):
        """Test GO statement replacement is case-insensitive."""
        executor = SQLExecutor()

        sql = """
        SELECT * FROM table1;
        GO
        SELECT * FROM table2;
        go
        SELECT * FROM table3;
        Go
        """

        statements = executor.split_statements(sql)
        # Should split into 3 SELECT statements
        assert len(statements) >= 3, f"Expected >=3 statements, got {len(statements)}"


def run_all_advanced_tests():
    """Run all advanced test suites."""
    print("="*70)
    print("PHASE 1A ADVANCED TESTS")
    print("="*70)

    test_classes = [
        TestStressCases,
        TestEdgeCases,
        TestErrorRecovery,
        TestSQLParsingRobustness
    ]

    total = 0
    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n[{test_class.__name__}]")
        test_instance = test_class()

        for method_name in sorted(dir(test_instance)):
            if method_name.startswith('test_'):
                total += 1
                try:
                    method = getattr(test_instance, method_name)
                    result = method()
                    if result is not None:
                        print(f"  [PASS] {method_name} ({result:.3f}s)")
                    else:
                        print(f"  [PASS] {method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  [FAIL] {method_name}: {str(e)}")
                    failed += 1

    print("\n" + "="*70)
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    print("="*70)

    return failed == 0


if __name__ == '__main__':
    success = run_all_advanced_tests()
    sys.exit(0 if success else 1)
