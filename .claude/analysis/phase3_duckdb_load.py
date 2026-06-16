"""
PHASE 3: DuckDB Population — Load cached Parquet files into local DuckDB + MotherDuck
"""
import os
import duckdb
from pathlib import Path
from datetime import datetime
import json

print("=" * 70)
print("PHASE 3: DuckDB POPULATION")
print("=" * 70)

# Initialize DuckDB
duckdb_path = os.getenv('DUCKDB_PATH', 'data/local_db/nyc_mission_control.duckdb')
conn = duckdb.connect(duckdb_path)

print(f"\n📊 Connecting to DuckDB: {duckdb_path}")
conn.execute("INSTALL parquet; LOAD parquet;")

# Load all cached Parquet files
cache_dir = Path('data/cache')
results = {}

print(f"\n📁 Loading from cache directory: {cache_dir}")

for parquet_file in sorted(cache_dir.glob('*.parquet')):
    table_name = parquet_file.stem
    
    try:
        print(f"  Loading {table_name:30s}... ", end='', flush=True)
        
        # Load into DuckDB
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} AS
            SELECT * FROM parquet_scan('{parquet_file}')
        """)
        
        # Get row count
        row_count = conn.execute(f"SELECT COUNT(*) as cnt FROM {table_name}").fetchall()[0][0]
        
        results[table_name] = {
            'rows': row_count,
            'status': 'SUCCESS'
        }
        
        print(f"✓ {row_count:,} rows")
        
    except Exception as e:
        results[table_name] = {
            'error': str(e)[:100],
            'status': 'FAILED'
        }
        print(f"✗ {str(e)[:50]}")

# List all tables
tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()

print(f"\n✅ Total tables in DuckDB: {len(tables)}")
for table in tables:
    print(f"   - {table[0]}")

# MotherDuck sync (if token available)
motherduck_token = os.getenv('MOTHERDUCK_TOKEN', '').strip()

if motherduck_token:
    print(f"\n☁️  MotherDuck Sync:")
    try:
        # Create MotherDuck connection
        md_conn = duckdb.connect('md:_my_db')
        
        for table_name, table_info in results.items():
            if table_info['status'] == 'SUCCESS':
                print(f"   Syncing {table_name}... ", end='', flush=True)
                
                # Copy table to MotherDuck
                data = conn.execute(f"SELECT * FROM {table_name}").fetch_arrow_table()
                md_conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM ?", [data])
                
                print("✓")
        
        print("   ✓ MotherDuck sync complete")
    except Exception as e:
        print(f"   ⚠️  MotherDuck sync failed: {str(e)[:50]}")
else:
    print("\n⚠️  MotherDuck token not set — skipping cloud sync")

# Save Phase 3 results
report_path = Path('.claude/analysis/phase3_report.json')
with open(report_path, 'w') as f:
    json.dump({
        'phase': 3,
        'timestamp': datetime.now().isoformat(),
        'duckdb_path': duckdb_path,
        'tables_loaded': len(results),
        'results': results
    }, f, indent=2)

print(f"\n📊 Phase 3 report: {report_path}")
print("=" * 70)

