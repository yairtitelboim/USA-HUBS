#!/bin/bash

# Phase 2 Complete Script
# This script runs all the steps for Phase 2:
# 1. Validates the data
# 2. Exports the combined GeoJSON
# 3. Generates visualizations
# 4. Opens the Deck.gl prototype

# Activate the Python environment
source loghub_env/bin/activate

# Set variables
COUNTY_SHP="/Users/yairtitelboim/Documents/Kernel/ALLAPPS/LOGhub/data/tl_2024_us_county/tl_2024_us_county.shp"
OUTPUT_DIR="qa"
FINAL_DATA_DIR="data/final"
COMBINED_GEOJSON="data/final/county_scores.geojson"
VALIDATION_DIR="data/validation"
USE_MOCK_DATA=true
HEIGHT_FIELD="confidence"

# Create directories if they don't exist
mkdir -p "$OUTPUT_DIR"
mkdir -p "$FINAL_DATA_DIR"
mkdir -p "$VALIDATION_DIR"

# Step 1: Generate static visualization
echo "=========================================="
echo "Generating static visualization..."
echo "=========================================="
python tools/create_static_us_map.py \
  --output "$OUTPUT_DIR/full_us_map.png" \
  --use-mock-data \
  --county-shp "$COUNTY_SHP"

# Step 2: Generate interactive visualization
echo "=========================================="
echo "Generating interactive visualization..."
echo "=========================================="
python tools/create_interactive_us_map.py \
  --output "$OUTPUT_DIR/full_us_map.html" \
  --use-mock-data \
  --county-shp "$COUNTY_SHP"

# Step 3: Generate 3D interactive visualization with confidence as height
echo "=========================================="
echo "Generating 3D interactive visualization (confidence as height)..."
echo "=========================================="
python tools/create_3d_interactive_map.py \
  --output "$OUTPUT_DIR/full_us_map_3d_confidence.html" \
  --height-field "confidence" \
  --use-mock-data \
  --county-shp "$COUNTY_SHP"

# Step 4: Generate 3D interactive visualization with tile_count as height
echo "=========================================="
echo "Generating 3D interactive visualization (tile_count as height)..."
echo "=========================================="
python tools/create_3d_interactive_map.py \
  --output "$OUTPUT_DIR/full_us_map_3d_tile_count.html" \
  --height-field "tile_count" \
  --use-mock-data \
  --county-shp "$COUNTY_SHP" \
  --export-geojson "$COMBINED_GEOJSON"

# Step 5: Validate the GeoJSON data
echo "=========================================="
echo "Validating GeoJSON data..."
echo "=========================================="
python tools/validate_data.py \
  --input "$COMBINED_GEOJSON" \
  --output "$VALIDATION_DIR/county_scores_validation.json" \
  --type geojson

# Check if validation was successful
if [ $? -ne 0 ]; then
  echo "Error: Data validation failed. Please check the validation report."
  exit 1
fi

# Step 6: Ask if the user wants to open the Deck.gl prototype
echo "=========================================="
echo "Phase 2 setup complete!"
echo "=========================================="
echo "Static visualization: $OUTPUT_DIR/full_us_map.png"
echo "Interactive visualization: $OUTPUT_DIR/full_us_map.html"
echo "3D interactive visualization (confidence): $OUTPUT_DIR/full_us_map_3d_confidence.html"
echo "3D interactive visualization (tile_count): $OUTPUT_DIR/full_us_map_3d_tile_count.html"
echo "Combined GeoJSON: $COMBINED_GEOJSON"
echo "Validation report: $VALIDATION_DIR/county_scores_validation.json"

read -p "Do you want to open the Deck.gl prototype? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  # Run the Deck.gl prototype
  ./run_deckgl_prototype.sh
else
  echo "You can run the Deck.gl prototype later using:"
  echo "./run_deckgl_prototype.sh"
fi

echo "Phase 2 setup complete!"
