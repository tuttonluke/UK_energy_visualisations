import json

import topojson as tp

geojson_path = "src/backend/static/gb-dno-license-areas-2024_wgs84.geojson"
topojson_path = "src/backend/static/gb-dno-license-areas-2024_wgs84.topojson"

with open(geojson_path, "r", encoding="utf-8") as f:
    geo_data = json.load(f)

# Convert to topojson with quantization
topo_data = tp.Topology(geo_data, prequantize=False).to_json()

with open(topojson_path, "w", encoding="utf-8") as f:
    f.write(topo_data)
