import re

with open('app/dash_layouts.py', 'r', encoding='utf-8') as f:
    text = f.read()

replacements = ["viz-curb-metal", "viz-planimetric", "viz-ramp-heatmap", "isochrone", "equity"]

for chart in replacements:
    text = re.sub(fr'(visualization_asset\("{chart}"[^)]+)\)', r'\1, tier="2")', text)

with open('app/dash_layouts.py', 'w', encoding='utf-8') as f:
    f.write(text)
