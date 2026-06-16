import re

with open('app/viz_engine.py', encoding='utf-8') as f:
    text = f.read()

parts = text.split('        insight = ')
for i in range(1, len(parts)):
    idx = parts[i].find('\n        return')
    if idx != -1:
        insight_str = parts[i][:idx]
        if insight_str.startswith('f"') and insight_str.endswith('"'):
            insight_str = 'f"' + insight_str[2:-1].replace('\n', r'\n') + '"'
        elif insight_str.startswith('"') and insight_str.endswith('"'):
            insight_str = '"' + insight_str[1:-1].replace('\n', r'\n') + '"'
        parts[i] = insight_str + parts[i][idx:]

with open('app/viz_engine.py', 'w', encoding='utf-8') as f:
    f.write('        insight = '.join(parts))
