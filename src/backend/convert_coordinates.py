import json
from shapely.geometry import shape, mapping
from shapely.ops import transform
import pyproj

# Coordinate transform: British National Grid (27700) -> To: Standard GPS Lat/Long (4326)
project_bng_to_wgs84 = pyproj.Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True).transform

with open("gb-dno-license-areas-2024.geojson", "r") as f:
    geojson_data = json.load(f)
reprojected_features = []

for feature in geojson_data["features"]:
    py_geometry = shape(feature["geometry"])
    reprojected_py_geometry = transform(project_bng_to_wgs84, py_geometry)
    feature["geometry"] = mapping(reprojected_py_geometry)
    reprojected_features.append(feature)
    
wgs84_geojson = {
    "type": "FeatureCollection",
    "features": reprojected_features
}

output_filename = "gb-dno-license-areas-2024_wgs84.geojson"
with open(output_filename, "w") as f:
    json.dump(wgs84_geojson, f)
