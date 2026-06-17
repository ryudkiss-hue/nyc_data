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
        
    dive_id = meta.get('id')
    title = meta['title']
    description = meta.get('description', '')
    
    if dive_id:
        print(f"Updating Dive: {title} ({dive_id})")
        try:
            con.execute(
                f"SELECT * FROM MD_UPDATE_DIVE_CONTENT(id => '{dive_id}'::UUID, content => ?)",
                [content]
            )
            print(f"  Success!")
        except Exception as e:
            print(f"  Failed: {e}")
    else:
        print(f"Creating New Dive: {title}")
        try:
            res = con.execute(
                "SELECT id FROM MD_CREATE_DIVE(title => ?, content => ?, description => ?)",
                [title, content, description]
            ).df()
            new_id = res['id'].iloc[0]
            print(f"  Created! New ID: {new_id}")
            # Update local metadata with the new ID
            meta['id'] = str(new_id)
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2)
        except Exception as e:
            print(f"  Failed to create: {e}")

print("All dives synchronized with MotherDuck.")
