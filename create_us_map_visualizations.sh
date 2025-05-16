#!/bin/bash

# Create U.S. map visualizations
# This script generates both static PNG and interactive HTML visualizations of the full U.S. map

# Activate the Python environment
source loghub_env/bin/activate

# Set variables
COUNTY_SHP="/Users/yairtitelboim/Documents/Kernel/ALLAPPS/LOGhub/data/tl_2024_us_county/tl_2024_us_county.shp"
OUTPUT_DIR="qa"
STATIC_NAME="full_us_map.png"
INTERACTIVE_NAME="full_us_map.html"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Generate static visualization
echo "Generating static visualization..."
python tools/create_static_us_map.py \
  --output "$OUTPUT_DIR/$STATIC_NAME" \
  --use-mock-data \
  --county-shp "$COUNTY_SHP"

# Generate interactive visualization
echo "Generating interactive visualization..."
python tools/create_interactive_us_map.py \
  --output "$OUTPUT_DIR/$INTERACTIVE_NAME" \
  --use-mock-data \
  --county-shp "$COUNTY_SHP"

echo "Visualizations created successfully!"
echo "Static visualization: $OUTPUT_DIR/$STATIC_NAME"
echo "Interactive visualization: $OUTPUT_DIR/$INTERACTIVE_NAME"
