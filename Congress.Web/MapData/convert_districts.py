import geopandas as gpd
from pathlib import Path

source = Path(r".\MapData\Extracted\tlgpkg_2026_us_legislative.gpkg")
output_dir = Path(r".\wwwroot\data")
output = output_dir / "congressional-districts-120.geojson"

output_dir.mkdir(parents=True, exist_ok=True)

print("Reading Congressional Districts layer...")

districts = gpd.read_file(
    source,
    layer="Congressional Districts"
)

print(f"Loaded {len(districts)} congressional districts.")
print("Columns:")
print(list(districts.columns))

print("Converting to WGS84...")

districts = districts.to_crs(epsg=4326)

print(f"Writing {output}...")

districts.to_file(
    output,
    driver="GeoJSON"
)

print("Done!")
print(f"Output: {output}")
print(f"Size: {output.stat().st_size:,} bytes")
