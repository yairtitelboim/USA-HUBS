#!/bin/bash

# Create Phase 2 visualizations
# This script generates all visualizations for Phase 2 and exports the combined GeoJSON

# Activate the Python environment
source loghub_env/bin/activate

# Set variables directly
COUNTY_SHP="/Users/yairtitelboim/Documents/Kernel/ALLAPPS/LOGhub/data/tl_2024_us_county/tl_2024_us_county.shp"
OUTPUT_DIR="qa"
FINAL_DATA_DIR="data/final"
COMBINED_GEOJSON="data/final/county_scores.geojson"
USE_MOCK_DATA=true
HEIGHT_FIELD="confidence"

# Create output directories if they don't exist
mkdir -p "$OUTPUT_DIR"
mkdir -p "$FINAL_DATA_DIR"

# Generate static visualization
echo "Generating static visualization..."
python tools/create_static_us_map.py \
  --output "$OUTPUT_DIR/full_us_map.png" \
  --use-mock-data \
  --county-shp "$COUNTY_SHP"

# Generate interactive visualization
echo "Generating interactive visualization..."
python tools/create_interactive_us_map.py \
  --output "$OUTPUT_DIR/full_us_map.html" \
  --use-mock-data \
  --county-shp "$COUNTY_SHP"

# Generate 3D interactive visualization with confidence as height
echo "Generating 3D interactive visualization (confidence as height)..."
python tools/create_3d_interactive_map.py \
  --output "$OUTPUT_DIR/full_us_map_3d_confidence.html" \
  --height-field "confidence" \
  --use-mock-data \
  --county-shp "$COUNTY_SHP"

# Generate 3D interactive visualization with tile_count as height
echo "Generating 3D interactive visualization (tile_count as height)..."
python tools/create_3d_interactive_map.py \
  --output "$OUTPUT_DIR/full_us_map_3d_tile_count.html" \
  --height-field "tile_count" \
  --use-mock-data \
  --county-shp "$COUNTY_SHP" \
  --export-geojson "$COMBINED_GEOJSON"

echo "Visualizations created successfully!"
echo "Static visualization: $OUTPUT_DIR/full_us_map.png"
echo "Interactive visualization: $OUTPUT_DIR/full_us_map.html"
echo "3D interactive visualization (confidence): $OUTPUT_DIR/full_us_map_3d_confidence.html"
echo "3D interactive visualization (tile_count): $OUTPUT_DIR/full_us_map_3d_tile_count.html"
echo "Combined GeoJSON: $COMBINED_GEOJSON"
