import duckdb
import os
import json

con = duckdb.connect('md:')
df = con.sql("SELECT id, title, description, required_resources FROM MD_LIST_DIVES()").df()

os.makedirs('dives', exist_ok=True)
for _, row in df.iterrows():
    try:
        dive_id = row['id']
        query = f"SELECT content FROM MD_GET_DIVE(id => '{dive_id}'::UUID)"
        source_df = con.sql(query).df()
        source = source_df['content'].iloc[0]
    except Exception as e:
        print(f"Failed to fetch {row['title']}: {e}")
        continue
    
    # Save the file
    safe_title = "".join([c if c.isalnum() else "_" for c in row['title']])
    folder = f"dives/{safe_title}"
    os.makedirs(folder, exist_ok=True)
    
    with open(f"{folder}/index.tsx", "w", encoding="utf-8") as f:
        f.write(source)
    
    # Safely handle potential UUIDs or arrays in required_resources
    import uuid
    def default_serializer(obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return str(obj)
        
    metadata = {
        "id": str(row['id']),
        "title": str(row['title']) if row['title'] else None,
        "description": str(row['description']) if row['description'] else None,
        "requiredResources": row['required_resources'].tolist() if hasattr(row['required_resources'], 'tolist') else row['required_resources']
    }
    
    with open(f"{folder}/dive_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=default_serializer)

print("Saved dives locally.")
