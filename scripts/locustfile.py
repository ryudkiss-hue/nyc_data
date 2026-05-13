"""
Locust load testing script for the NYC DOT Toolkit.
Tests both the NiceGUI frontend responsiveness and the FastAPI backend endpoints.
"""
from locust import HttpUser, task, between

class MissionControlUser(HttpUser):
    # Simulate users clicking around every 1 to 3 seconds
    wait_time = between(1, 3)

    @task(3)
    def load_nicegui_frontend(self):
        """Test the main NiceGUI dashboard load performance."""
        self.client.get("/")

    @task(2)
    def check_api_health(self):
        """Test the FastAPI health endpoint."""
        self.client.get("/health")

    @task(2)
    def list_tables(self):
        """Test the DuckDB table listing endpoint."""
        self.client.get("/tables")

    @task(1)
    def simulate_cost_analysis(self):
        """Test the heavy cost analysis processing endpoint."""
        payload = [
            {"estimated_sqft": 150.5, "scope": "sidewalk_repair", "borough": "MANHATTAN"},
            {"estimated_sqft": 300.0, "scope": "pedestrian_ramp", "borough": "BROOKLYN"},
            {"estimated_sqft": 45.2, "scope": "curb_replacement", "borough": "QUEENS"}
        ]
        self.client.post("/analyze/costs", json=payload)
        
    @task(1)
    def simulate_quality_analysis(self):
        """Test the data quality scoring endpoint."""
        payload = [
            {"id": 1, "borough": "MANHATTAN", "status": "open"},
            {"id": 2, "borough": "BROOKLYN", "status": "closed"}
        ]
        self.client.post("/analyze/quality", json=payload)