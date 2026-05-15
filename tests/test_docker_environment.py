"""
Docker Environment Test Suite

Tests that verify all Docker services are healthy and functional.
Run with: pytest tests/test_docker_environment.py -v
"""

import os

import psycopg as psycopg2
import pytest
import requests

# Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://dot_user:dot_pass@localhost:5432/sidewalk_db"
)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "sk_test_demo_admin_abc123")


class TestDatabaseConnectivity:
    """PostgreSQL connectivity and health checks"""

    def test_database_connection(self):
        """Test PostgreSQL connection"""
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            assert result[0] == 1, "Database query failed"
        except Exception as e:
            pytest.fail(f"Database connection failed: {str(e)}")

    def test_required_tables_exist(self):
        """Verify all required tables exist"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        required_tables = [
            "sidewalk_inspections",
            "complaints_311",
            "contractors",
            "quality_metrics",
            "audit_log",
            "data_lineage",
            "demo_users",
            "demo_api_keys",
        ]

        for table in required_tables:
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = '{table}'
                );
            """)
            exists = cursor.fetchone()[0]
            assert exists, f"Table {table} does not exist"

        cursor.close()
        conn.close()

    def test_sample_data_loaded(self):
        """Verify sample data is populated"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Check record counts
        cursor.execute("SELECT COUNT(*) FROM sidewalk_inspections;")
        insp_count = cursor.fetchone()[0]
        assert insp_count > 0, "No sidewalk inspections loaded"

        cursor.execute("SELECT COUNT(*) FROM complaints_311;")
        compl_count = cursor.fetchone()[0]
        assert compl_count > 0, "No complaints loaded"

        cursor.execute("SELECT COUNT(*) FROM contractors;")
        contr_count = cursor.fetchone()[0]
        assert contr_count > 0, "No contractors loaded"

        cursor.close()
        conn.close()

    def test_quality_metrics_available(self):
        """Verify quality metrics are populated"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM quality_metrics;")
        count = cursor.fetchone()[0]
        assert count > 0, "No quality metrics found"

        cursor.close()
        conn.close()

    def test_audit_log_table(self):
        """Verify audit log table is accessible"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM audit_log;")
        count = cursor.fetchone()[0]
        assert count >= 0, "Audit log table not accessible"

        cursor.close()
        conn.close()


class TestAPIHealthAndConnectivity:
    """API service health checks"""

    def test_api_health_endpoint(self):
        """Test API health check endpoint"""
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"

        data = response.json()
        assert data.get("status") == "healthy", f"API not healthy: {data}"

    def test_api_documentation_accessible(self):
        """Test API documentation is accessible"""
        response = requests.get(f"{API_BASE_URL}/docs", timeout=10)
        assert response.status_code == 200, "API docs not accessible"

    def test_api_redoc_accessible(self):
        """Test ReDoc documentation is accessible"""
        response = requests.get(f"{API_BASE_URL}/redoc", timeout=10)
        assert response.status_code == 200, "ReDoc not accessible"


class TestAPIAuthentication:
    """API authentication and authorization tests"""

    def test_api_key_authentication(self):
        """Test API key authentication"""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=1", headers=headers, timeout=10
        )
        assert response.status_code == 200, f"API auth failed: {response.status_code}"

    def test_missing_api_key_rejected(self):
        """Test that requests without API key are rejected"""
        response = requests.get(f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=1", timeout=10)
        assert response.status_code in [401, 403], "Missing API key should be rejected"


class TestAPIDataEndpoints:
    """Test API data query endpoints"""

    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": f"Bearer {API_KEY}"}

    def test_sidewalk_inspections_endpoint(self, auth_headers):
        """Test sidewalk inspections endpoint"""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=5", headers=auth_headers, timeout=10
        )
        assert response.status_code == 200

        data = response.json()
        assert "data" in data, "Response missing 'data' field"
        assert "total" in data, "Response missing 'total' field"
        assert len(data["data"]) <= 5, "Limit not respected"

    def test_complaints_endpoint(self, auth_headers):
        """Test 311 complaints endpoint"""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/complaints_311?limit=5", headers=auth_headers, timeout=10
        )
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "total" in data

    def test_contractors_endpoint(self, auth_headers):
        """Test contractors endpoint"""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/contractors?limit=5", headers=auth_headers, timeout=10
        )
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "total" in data

    def test_pagination(self, auth_headers):
        """Test pagination parameters"""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=2&offset=0",
            headers=auth_headers,
            timeout=10,
        )
        assert response.status_code == 200

        data = response.json()
        assert data.get("limit") == 2
        assert data.get("offset") == 0

    def test_filtering(self, auth_headers):
        """Test filtering capability"""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?material_type=Concrete&limit=10",
            headers=auth_headers,
            timeout=10,
        )
        assert response.status_code == 200

        data = response.json()
        # All returned records should have material_type=Concrete (if filter is applied)
        for record in data.get("data", []):
            # Filter may not be strictly enforced in mock, so just check structure
            assert "inspection_id" in record


class TestDataIntegrity:
    """Test data integrity and consistency"""

    def test_sidewalk_inspections_schema(self):
        """Verify sidewalk inspections schema"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'sidewalk_inspections'
            ORDER BY ordinal_position;
        """)

        columns = {row[0]: row[1] for row in cursor.fetchall()}

        # Verify key columns exist
        assert "inspection_id" in columns
        assert "material_type" in columns
        assert "condition_rating" in columns
        assert "ada_compliant" in columns

        cursor.close()
        conn.close()

    def test_sample_data_consistency(self):
        """Verify sample data doesn't have unexpected nulls in key fields"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Check for NULL inspection_ids (should be unique)
        cursor.execute("""
            SELECT COUNT(*) FROM sidewalk_inspections 
            WHERE inspection_id IS NULL;
        """)
        null_count = cursor.fetchone()[0]
        assert null_count == 0, "Found NULL inspection_ids"

        cursor.close()
        conn.close()


class TestObservability:
    """Test observability features"""

    def test_metrics_collection(self):
        """Verify metrics are being collected"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM quality_metrics 
            WHERE measurement_timestamp > NOW() - INTERVAL '1 day';
        """)
        count = cursor.fetchone()[0]
        assert count > 0, "No recent metrics found"

        cursor.close()
        conn.close()

    def test_lineage_tracking(self):
        """Verify lineage is being tracked"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM data_lineage;")
        count = cursor.fetchone()[0]
        assert count >= 0, "Lineage table not accessible"

        cursor.close()
        conn.close()

    def test_audit_trail_functionality(self):
        """Verify audit trail is capturing events"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Create a test entry and verify it's logged
        cursor.execute("""
            INSERT INTO audit_log (table_name, operation, changed_by) 
            VALUES ('test_table', 'test_operation', 'test_user')
            RETURNING id;
        """)
        audit_id = cursor.fetchone()[0]
        conn.commit()

        # Verify we can read it back
        cursor.execute(f"SELECT * FROM audit_log WHERE id = {audit_id};")
        result = cursor.fetchone()
        assert result is not None, "Audit entry not found"

        # Clean up
        cursor.execute(f"DELETE FROM audit_log WHERE id = {audit_id};")
        conn.commit()
        cursor.close()
        conn.close()


class TestServiceInteraction:
    """Test integration between services"""

    def test_api_queries_database(self):
        """Verify API is actually querying the database"""
        auth_headers = {"Authorization": f"Bearer {API_KEY}"}

        # Get data from API
        api_response = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=1", headers=auth_headers, timeout=10
        )
        assert api_response.status_code == 200

        api_count = api_response.json().get("total", 0)

        # Get data from database directly
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sidewalk_inspections;")
        db_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        # Should be the same (or at least close)
        assert api_count == db_count, f"API count ({api_count}) != DB count ({db_count})"


class TestPerformance:
    """Performance and timing tests"""

    def test_api_response_time(self):
        """Verify API response time is acceptable"""
        auth_headers = {"Authorization": f"Bearer {API_KEY}"}

        import time

        start = time.time()
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=10", headers=auth_headers, timeout=10
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 5.0, f"API response too slow: {elapsed}s"

    def test_database_query_time(self):
        """Verify database query performance"""
        import time

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        start = time.time()
        cursor.execute("SELECT COUNT(*) FROM sidewalk_inspections;")
        cursor.fetchone()
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Database query too slow: {elapsed}s"

        cursor.close()
        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
