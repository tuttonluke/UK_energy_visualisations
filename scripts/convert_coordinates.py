import json
import os

import pyproj
from shapely.geometry import mapping, shape
from shapely.ops import transform

# Coordinate transform: British National Grid (27700) -> To: Standard GPS Lat/Long (4326)
project_bng_to_wgs84 = pyproj.Transformer.from_crs(
    "EPSG:27700", "EPSG:4326", always_xy=True
).transform


script_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(script_dir, "..", "gb-dno-license-areas-2024.geojson")

with open(input_file, "r") as f:
    geojson_data = json.load(f)
reprojected_features = []

for feature in geojson_data["features"]:
    py_geometry = shape(feature["geometry"])
    reprojected_py_geometry = transform(project_bng_to_wgs84, py_geometry)
    feature["geometry"] = mapping(reprojected_py_geometry)
    reprojected_features.append(feature)

wgs84_geojson = {"type": "FeatureCollection", "features": reprojected_features}

output_filename = os.path.join(
    script_dir, "..", "gb-dno-license-areas-2024_wgs84.geojson"
)
with open(output_filename, "w") as f:
    json.dump(wgs84_geojson, f)
