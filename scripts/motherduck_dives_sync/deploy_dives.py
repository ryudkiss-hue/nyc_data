import duckdb
import json
import glob
import os

con = duckdb.connect('md:')

metadata_files = glob.glob('dives/**/dive_metadata.json', recursive=True)

for meta_file in metadata_files:
    folder = os.path.dirname(meta_file)
    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    with open(f"{folder}/index.tsx", 'r', encoding='utf-8') as f:
        content = f.read()
        
    dive_id = meta['id']
    title = meta['title']
    
    print(f"Updating Dive: {title} ({dive_id})")
    try:
        # Prepare the query using bound parameters to avoid SQL injection / quote issues
        con.execute(
            f"SELECT * FROM MD_UPDATE_DIVE_CONTENT(id => '{dive_id}'::UUID, content => ?)",
            [content]
        )
        print(f"  Success!")
    except Exception as e:
        print(f"  Failed: {e}")

print("All dives synchronized with MotherDuck.")
