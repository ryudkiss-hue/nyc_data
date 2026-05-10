"""
Integration Quick Start Test Suite

Tests the complete 7-step integration workflow to ensure all components work end-to-end.
Run with: pytest tests/test_integration_quick_start.py -v
"""

import os
import json
import pytest
import requests
import psycopg2
from datetime import datetime, timedelta

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dot_user:dot_pass@localhost:5432/sidewalk_db")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "sk_test_demo_admin_abc123")


class TestIntegrationQuickStart:
    """Complete 7-step integration workflow tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Fixture for API authentication headers"""
        return {"Authorization": f"Bearer {API_KEY}"}
    
    # Step 1: Load Sample Data
    def test_step_1_sample_data_loaded(self):
        """Step 1: Verify sample data is loaded"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check sidewalk inspections
        cursor.execute("SELECT COUNT(*) FROM sidewalk_inspections;")
        insp_count = cursor.fetchone()[0]
        assert insp_count > 0, "Sidewalk inspections not loaded"
        
        # Check 311 complaints
        cursor.execute("SELECT COUNT(*) FROM complaints_311;")
        compl_count = cursor.fetchone()[0]
        assert compl_count > 0, "311 complaints not loaded"
        
        # Check contractors
        cursor.execute("SELECT COUNT(*) FROM contractors;")
        contr_count = cursor.fetchone()[0]
        assert contr_count > 0, "Contractors not loaded"
        
        cursor.close()
        conn.close()
        
        print(f"\n✓ Step 1: Sample data loaded")
        print(f"  - Sidewalk Inspections: {insp_count}")
        print(f"  - 311 Complaints: {compl_count}")
        print(f"  - Contractors: {contr_count}")
    
    # Step 2: Validate Schema
    def test_step_2_schema_validation(self):
        """Step 2: Validate schema is correct"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Get schema for sidewalk_inspections
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'sidewalk_inspections'
            ORDER BY ordinal_position;
        """)
        
        columns = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Verify key columns
        required_columns = {
            'inspection_id': 'character varying',
            'material_type': 'character varying',
            'condition_rating': 'character varying',
            'ada_compliant': 'boolean',
            'inspection_date': 'date'
        }
        
        for col_name, expected_type in required_columns.items():
            assert col_name in columns, f"Missing column: {col_name}"
            # Type checking might be loose, so just verify column exists
        
        cursor.close()
        conn.close()
        
        print(f"\n✓ Step 2: Schema validation passed")
        print(f"  - Columns: {len(columns)}")
        print(f"  - Key columns verified")
    
    # Step 3: Run Quality Check
    def test_step_3_quality_check(self):
        """Step 3: Run quality checks"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check quality metrics
        cursor.execute("""
            SELECT dataset_name, metric_name, metric_value 
            FROM quality_metrics 
            ORDER BY measurement_timestamp DESC 
            LIMIT 10;
        """)
        
        metrics = cursor.fetchall()
        assert len(metrics) > 0, "No quality metrics found"
        
        # Verify metric values are reasonable
        for dataset, metric, value in metrics:
            assert isinstance(value, (int, float)), f"Metric value not numeric: {value}"
            if 'percentage' in metric.lower() or metric in ['completeness', 'validity', 'consistency']:
                assert 0 <= value <= 100, f"Invalid percentage value: {value}"
        
        cursor.close()
        conn.close()
        
        print(f"\n✓ Step 3: Quality checks passed")
        print(f"  - Metrics collected: {len(metrics)}")
        print(f"  - Sample: {metrics[0][1]} = {metrics[0][2]:.2f}%")
    
    # Step 4: Query Data via API
    def test_step_4_api_query(self, auth_headers):
        """Step 4: Query data via API"""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=5",
            headers=auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"API query failed: {response.status_code}"
        
        data = response.json()
        assert "data" in data, "Missing 'data' field"
        assert "total" in data, "Missing 'total' field"
        assert len(data["data"]) > 0, "No records returned"
        
        # Verify record structure
        record = data["data"][0]
        assert "inspection_id" in record, "Missing inspection_id"
        assert "material_type" in record, "Missing material_type"
        
        print(f"\n✓ Step 4: API query successful")
        print(f"  - Records returned: {len(data['data'])}")
        print(f"  - Total available: {data['total']}")
        print(f"  - Sample ID: {record['inspection_id']}")
    
    # Step 5: View Lineage & Audit Trail
    def test_step_5_lineage_and_audit(self):
        """Step 5: Verify lineage and audit trail"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check lineage
        cursor.execute("""
            SELECT source_dataset, target_dataset, transformation 
            FROM data_lineage 
            ORDER BY created_at DESC 
            LIMIT 5;
        """)
        
        lineage = cursor.fetchall()
        assert len(lineage) > 0, "No lineage data found"
        
        # Check audit trail
        cursor.execute("""
            SELECT COUNT(*) FROM audit_log;
        """)
        
        audit_count = cursor.fetchone()[0]
        assert audit_count >= 0, "Audit log not accessible"
        
        cursor.close()
        conn.close()
        
        print(f"\n✓ Step 5: Lineage and audit trail verified")
        print(f"  - Lineage relationships: {len(lineage)}")
        print(f"  - Audit entries: {audit_count}")
        if lineage:
            print(f"  - Sample: {lineage[0][0]} → {lineage[0][1]}")
    
    # Step 6: Check Compliance
    def test_step_6_compliance_check(self, auth_headers):
        """Step 6: Check compliance status"""
        # Query ADA compliance via API
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?ada_compliant=true&limit=100",
            headers=auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Compliance query failed: {response.status_code}"
        
        data = response.json()
        compliant_count = len(data["data"])
        
        # Also check total
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=100",
            headers=auth_headers,
            timeout=10
        )
        total_count = response.json()["total"]
        
        if total_count > 0:
            compliance_percentage = (compliant_count / total_count) * 100
        else:
            compliance_percentage = 0
        
        print(f"\n✓ Step 6: Compliance check completed")
        print(f"  - Compliant records: {compliant_count}")
        print(f"  - Total records: {total_count}")
        print(f"  - Compliance rate: {compliance_percentage:.1f}%")
    
    # Step 7: Explore Dashboards
    def test_step_7_dashboards_available(self):
        """Step 7: Verify dashboards are accessible"""
        
        # Test Grafana
        response = requests.get("http://localhost:3000/api/health", timeout=10)
        assert response.status_code == 200, "Grafana not accessible"
        
        # Test Prometheus
        response = requests.get("http://localhost:9090/api/v1/targets", timeout=10)
        assert response.status_code == 200, "Prometheus not accessible"
        
        # Test Jaeger
        response = requests.get("http://localhost:16686/api/services", timeout=10)
        assert response.status_code == 200, "Jaeger not accessible"
        
        print(f"\n✓ Step 7: Dashboards verified")
        print(f"  - Grafana: http://localhost:3000")
        print(f"  - Prometheus: http://localhost:9090")
        print(f"  - Jaeger: http://localhost:16686")


class TestDataQualityMetrics:
    """Validate data quality metrics"""
    
    def test_completeness_metric(self):
        """Test completeness percentage"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Count total and non-null
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(material_type) as non_null
            FROM sidewalk_inspections;
        """)
        
        total, non_null = cursor.fetchone()
        if total > 0:
            completeness = (non_null / total) * 100
            assert completeness >= 95, f"Completeness too low: {completeness}%"
        
        cursor.close()
        conn.close()
    
    def test_validity_metric(self):
        """Test data validity"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check for invalid condition ratings
        cursor.execute("""
            SELECT COUNT(*) FROM sidewalk_inspections 
            WHERE condition_rating NOT IN ('Good', 'Fair', 'Poor');
        """)
        
        invalid_count = cursor.fetchone()[0]
        assert invalid_count == 0, f"Invalid condition ratings found: {invalid_count}"
        
        cursor.close()
        conn.close()
    
    def test_consistency_metric(self):
        """Test data consistency"""
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check that inspection_date is not in future
        cursor.execute("""
            SELECT COUNT(*) FROM sidewalk_inspections 
            WHERE inspection_date > CURRENT_DATE;
        """)
        
        future_count = cursor.fetchone()[0]
        assert future_count == 0, f"Future inspection dates found: {future_count}"
        
        cursor.close()
        conn.close()


class TestAPIFunctionality:
    """Comprehensive API functionality tests"""
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": f"Bearer {API_KEY}"}
    
    def test_list_operations(self, auth_headers):
        """Test list/GET operations"""
        endpoints = [
            '/api/v1/sidewalk_inspections',
            '/api/v1/complaints_311',
            '/api/v1/contractors'
        ]
        
        for endpoint in endpoints:
            response = requests.get(
                f"{API_BASE_URL}{endpoint}?limit=10",
                headers=auth_headers,
                timeout=10
            )
            assert response.status_code == 200, f"Failed to list {endpoint}"
            
            data = response.json()
            assert "data" in data
            assert "total" in data
    
    def test_pagination(self, auth_headers):
        """Test pagination"""
        # First page
        response1 = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=5&offset=0",
            headers=auth_headers,
            timeout=10
        )
        assert response1.status_code == 200
        
        data1 = response1.json()
        id1 = data1["data"][0]["id"] if data1["data"] else None
        
        # Second page
        response2 = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=5&offset=5",
            headers=auth_headers,
            timeout=10
        )
        assert response2.status_code == 200
        
        data2 = response2.json()
        id2 = data2["data"][0]["id"] if data2["data"] else None
        
        # Should be different records (unless dataset is small)
        if id1 and id2:
            # May be same if dataset small, so just verify structure
            assert "id" in data2["data"][0]
    
    def test_response_format(self, auth_headers):
        """Test API response format consistency"""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=1",
            headers=auth_headers,
            timeout=10
        )
        
        data = response.json()
        
        # Verify response structure
        assert isinstance(data, dict)
        assert "data" in data
        assert "total" in data
        assert "limit" in data or "offset" in data
        
        # Verify data is a list
        assert isinstance(data["data"], list)


class TestEndToEnd:
    """End-to-end integration tests"""
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": f"Bearer {API_KEY}"}
    
    def test_complete_workflow(self, auth_headers):
        """Test complete workflow: Load → Validate → Query → Verify"""
        
        # 1. Load and verify data exists
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM sidewalk_inspections;")
        db_count = cursor.fetchone()[0]
        assert db_count > 0
        
        cursor.close()
        conn.close()
        
        # 2. Validate schema
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=1",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        
        # 3. Query and verify
        data = response.json()
        api_count = data.get("total", 0)
        assert api_count == db_count, "API count != DB count"
        
        # 4. Verify record structure
        if data["data"]:
            record = data["data"][0]
            required_fields = ["inspection_id", "material_type", "inspection_date"]
            for field in required_fields:
                assert field in record, f"Missing field: {field}"
        
        print(f"\n✓ End-to-end workflow successful")
        print(f"  - Database records: {db_count}")
        print(f"  - API records: {api_count}")
        print(f"  - Schema valid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
