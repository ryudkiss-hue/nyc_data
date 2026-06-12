"""
Verification script for Task 1: Spatial Migration to DuckDB.
Demonstrates ST_Intersects join between 311 complaints and sidewalk polygons.
"""
import os
import sys
from pathlib import Path
import pandas as pd

# Path resolution
_src_path = str((Path(__file__).resolve().parent.parent / "src").absolute())
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from socrata_toolkit.core.duckdb_store import DuckDBManager, DuckDBRepository

def verify_spatial_migration():
    print("--- Starting Spatial Migration Verification ---")
    
    db_path = "data/local_db/spatial_verify.duckdb"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    mgr = DuckDBManager(db_path)
    
    # 1. Mock 311 Complaints (Points)
    complaints_df = pd.DataFrame([
        {"id": "C1", "latitude": 40.7128, "longitude": -74.0060, "type": "Sidewalk Pothole"},
        {"id": "C2", "latitude": 40.7831, "longitude": -73.9712, "type": "Curb Damage"}
    ])
    
    repo_311 = DuckDBRepository(mgr, "verify_311")
    repo_311.upsert_dataframe(complaints_df, "id")
    print("✅ Ingested mock 311 complaints (Point detection)")
    
    # 2. Mock Sidewalk Polygons (WKT)
    # C1 is inside this polygon, C2 is outside.
    sidewalk_df = pd.DataFrame([
        {
            "bbl": "1000010001", 
            "the_geom": "POLYGON ((-74.01 40.71, -74.00 40.71, -74.00 40.72, -74.01 40.72, -74.01 40.71))",
            "material": "Concrete"
        }
    ])
    
    repo_sidewalk = DuckDBRepository(mgr, "verify_sidewalks")
    repo_sidewalk.upsert_dataframe(sidewalk_df, "bbl")
    print("✅ Ingested mock sidewalk polygons (WKT detection)")
    
    # 3. Spatial Join Query (Requested Sample)
    print("\n--- Running Spatial Join (ST_Intersects) ---")
    query = """
        SELECT 
            c.id as complaint_id,
            c.type as complaint_type,
            s.bbl as sidewalk_bbl,
            s.material as sidewalk_material
        FROM verify_311 c
        JOIN verify_sidewalks s 
          ON ST_Intersects(c.native_geom, s.native_geom)
    """
    
    results = mgr.conn.execute(query).df()
    print("Join Results:")
    print(results)
    
    if len(results) == 1 and results.iloc[0]['complaint_id'] == 'C1':
        print("\n🎉 Task 1 Verification SUCCESS: C1 correctly matched to sidewalk polygon.")
    else:
        print("\n❌ Verification FAILED: Results do not match expectation.")
        
    mgr.close()

if __name__ == "__main__":
    verify_spatial_migration()