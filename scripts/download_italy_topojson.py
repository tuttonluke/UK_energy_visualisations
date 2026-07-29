import urllib.request
import os

url = "https://raw.githubusercontent.com/openpolis/geojson-italy/master/topojson/limits_IT_regions.topo.json"
output_path = os.path.join("src", "backend", "static", "italy.topojson")

print(f"Downloading Italy TopoJSON to {output_path}...")
urllib.request.urlretrieve(url, output_path)
print("Done.")
