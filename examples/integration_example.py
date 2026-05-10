#!/usr/bin/env python3
"""
NYC Data Toolkit - Integration Example

Complete end-to-end example demonstrating:
1. Database connection and schema verification
2. Data ingestion and validation
3. Quality checks
4. API access
5. Lineage tracking
6. Data querying
"""

import os
import sys
import json
import requests
import psycopg2
from datetime import datetime
from typing import Dict, List, Any

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dot_user:dot_pass@localhost:5432/sidewalk_db")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "sk_test_demo_admin_abc123")

class IntegrationExample:
    """Complete integration example with logging and error handling"""
    
    def __init__(self):
        self.db_conn = None
        self.api_session = None
        self.start_time = datetime.now()
        self.results = {
            "started_at": self.start_time.isoformat(),
            "steps": []
        }
    
    def log(self, step: str, status: str, message: str = ""):
        """Log step progress"""
        print(f"\n[{status:>5}] {step}")
        if message:
            print(f"        {message}")
        
        self.results["steps"].append({
            "step": step,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def connect_database(self) -> bool:
        """Step 1: Connect to PostgreSQL database"""
        try:
            self.log("Database Connection", "...", "Connecting to PostgreSQL...")
            self.db_conn = psycopg2.connect(DATABASE_URL)
            
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            
            self.log("Database Connection", "OK", f"Connected: {version.split(',')[0]}")
            return True
        except Exception as e:
            self.log("Database Connection", "FAIL", str(e))
            return False
    
    def verify_schema(self) -> bool:
        """Step 2: Verify all required tables exist"""
        try:
            self.log("Schema Verification", "...", "Checking tables...")
            cursor = self.db_conn.cursor()
            
            # Check for key tables
            required_tables = [
                'sidewalk_inspections',
                'complaints_311',
                'contractors',
                'quality_metrics',
                'audit_log',
                'data_lineage'
            ]
            
            tables_found = []
            for table in required_tables:
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    );
                """)
                exists = cursor.fetchone()[0]
                if exists:
                    tables_found.append(table)
            
            cursor.close()
            
            status = "OK" if len(tables_found) == len(required_tables) else "WARN"
            self.log("Schema Verification", status, f"Found {len(tables_found)}/{len(required_tables)} tables")
            return len(tables_found) > 0
        except Exception as e:
            self.log("Schema Verification", "FAIL", str(e))
            return False
    
    def check_sample_data(self) -> bool:
        """Step 3: Verify sample data is loaded"""
        try:
            self.log("Sample Data Check", "...", "Checking loaded data...")
            cursor = self.db_conn.cursor()
            
            # Check record counts
            cursor.execute("SELECT COUNT(*) FROM sidewalk_inspections;")
            insp_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM complaints_311;")
            compl_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM contractors;")
            contr_count = cursor.fetchone()[0]
            
            cursor.close()
            
            total = insp_count + compl_count + contr_count
            message = f"Inspections: {insp_count}, Complaints: {compl_count}, Contractors: {contr_count}"
            
            status = "OK" if total > 0 else "WARN"
            self.log("Sample Data Check", status, message)
            return total > 0
        except Exception as e:
            self.log("Sample Data Check", "FAIL", str(e))
            return False
    
    def check_quality_metrics(self) -> bool:
        """Step 4: Verify quality metrics are available"""
        try:
            self.log("Quality Metrics", "...", "Checking metrics...")
            cursor = self.db_conn.cursor()
            
            cursor.execute("""
                SELECT dataset_name, metric_name, metric_value 
                FROM quality_metrics 
                ORDER BY measurement_timestamp DESC 
                LIMIT 10;
            """)
            
            metrics = cursor.fetchall()
            cursor.close()
            
            if metrics:
                sample = metrics[0]
                message = f"Found {len(metrics)} metrics. Sample: {sample[0]} - {sample[1]}: {sample[2]:.2f}%"
                self.log("Quality Metrics", "OK", message)
                return True
            else:
                self.log("Quality Metrics", "WARN", "No metrics found")
                return True
        except Exception as e:
            self.log("Quality Metrics", "FAIL", str(e))
            return False
    
    def test_api_health(self) -> bool:
        """Step 5: Test API health endpoint"""
        try:
            self.log("API Health Check", "...", f"Testing {API_BASE_URL}/health...")
            
            response = requests.get(f"{API_BASE_URL}/health", timeout=10)
            
            if response.status_code == 200:
                health = response.json()
                self.log("API Health Check", "OK", f"Status: {health.get('status', 'unknown')}")
                return True
            else:
                self.log("API Health Check", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("API Health Check", "FAIL", str(e))
            return False
    
    def test_api_authentication(self) -> bool:
        """Step 6: Test API authentication with key"""
        try:
            self.log("API Authentication", "...", f"Testing with API key...")
            
            headers = {"Authorization": f"Bearer {API_KEY}"}
            response = requests.get(
                f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=1",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('data', []))
                self.log("API Authentication", "OK", f"Got {count} record(s)")
                return True
            else:
                self.log("API Authentication", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("API Authentication", "FAIL", str(e))
            return False
    
    def query_sample_data(self) -> bool:
        """Step 7: Query sample data via API"""
        try:
            self.log("API Data Query", "...", "Querying sidewalk inspections...")
            
            headers = {"Authorization": f"Bearer {API_KEY}"}
            response = requests.get(
                f"{API_BASE_URL}/api/v1/sidewalk_inspections?limit=5",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                records = data.get('data', [])
                total = data.get('total', 0)
                
                message = f"Retrieved 5 records from total of {total}"
                if records:
                    first_record = records[0]
                    message += f". Sample: {first_record.get('inspection_id', 'N/A')}"
                
                self.log("API Data Query", "OK", message)
                
                # Pretty print sample
                print(f"\n        Sample record (first of 5):")
                print(f"        {json.dumps(records[0], indent=8, default=str)}")
                
                return True
            else:
                self.log("API Data Query", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("API Data Query", "FAIL", str(e))
            return False
    
    def check_lineage(self) -> bool:
        """Step 8: Verify data lineage is tracked"""
        try:
            self.log("Data Lineage", "...", "Checking lineage...")
            cursor = self.db_conn.cursor()
            
            cursor.execute("""
                SELECT source_dataset, target_dataset, transformation 
                FROM data_lineage 
                LIMIT 5;
            """)
            
            lineage = cursor.fetchall()
            cursor.close()
            
            if lineage:
                message = f"Found {len(lineage)} lineage relationships"
                sample = lineage[0]
                message += f". Example: {sample[0]} → {sample[1]}"
                self.log("Data Lineage", "OK", message)
                return True
            else:
                self.log("Data Lineage", "WARN", "No lineage records found")
                return True
        except Exception as e:
            self.log("Data Lineage", "FAIL", str(e))
            return False
    
    def check_audit_trail(self) -> bool:
        """Step 9: Verify audit logging is working"""
        try:
            self.log("Audit Trail", "...", "Checking audit logs...")
            cursor = self.db_conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM audit_log;
            """)
            
            count = cursor.fetchone()[0]
            cursor.close()
            
            status = "OK" if count > 0 else "WARN"
            message = f"Found {count} audit entries"
            self.log("Audit Trail", status, message)
            return True
        except Exception as e:
            self.log("Audit Trail", "FAIL", str(e))
            return False
    
    def test_geospatial_query(self) -> bool:
        """Step 10: Test geospatial capabilities"""
        try:
            self.log("Geospatial Query", "...", "Testing location-based query...")
            
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM sidewalk_inspections 
                WHERE location IS NOT NULL;
            """)
            
            count = cursor.fetchone()[0]
            cursor.close()
            
            if count > 0:
                self.log("Geospatial Query", "OK", f"Found {count} records with location data")
                return True
            else:
                self.log("Geospatial Query", "WARN", "No location data found")
                return True
        except Exception as e:
            self.log("Geospatial Query", "FAIL", str(e))
            return False
    
    def run_all_checks(self) -> bool:
        """Execute all integration checks"""
        print("\n" + "="*60)
        print("NYC Data Toolkit - Integration Example")
        print("="*60)
        
        steps = [
            ("Database Connection", self.connect_database),
            ("Schema Verification", self.verify_schema),
            ("Sample Data Check", self.check_sample_data),
            ("Quality Metrics", self.check_quality_metrics),
            ("API Health Check", self.test_api_health),
            ("API Authentication", self.test_api_authentication),
            ("API Data Query", self.query_sample_data),
            ("Data Lineage", self.check_lineage),
            ("Audit Trail", self.check_audit_trail),
            ("Geospatial Query", self.test_geospatial_query),
        ]
        
        results = []
        for step_name, step_func in steps:
            try:
                result = step_func()
                results.append(result)
            except Exception as e:
                self.log(step_name, "ERROR", str(e))
                results.append(False)
        
        # Summary
        passed = sum(results)
        total = len(results)
        
        print("\n" + "="*60)
        print(f"Summary: {passed}/{total} checks passed")
        print("="*60)
        
        self.results["completed_at"] = datetime.now().isoformat()
        self.results["summary"] = {
            "passed": passed,
            "total": total,
            "success": passed == total
        }
        
        return passed == total
    
    def save_results(self, filename: str = "integration_results.json"):
        """Save results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            print(f"\nResults saved to {filename}")
        except Exception as e:
            print(f"Failed to save results: {e}")
    
    def cleanup(self):
        """Close database connection"""
        if self.db_conn:
            self.db_conn.close()

def main():
    """Main entry point"""
    example = IntegrationExample()
    
    try:
        success = example.run_all_checks()
        example.save_results()
        
        return 0 if success else 1
    except Exception as e:
        print(f"\nFatal error: {e}")
        return 1
    finally:
        example.cleanup()

if __name__ == "__main__":
    sys.exit(main())
