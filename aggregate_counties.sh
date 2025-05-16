#!/bin/bash

# Aggregate tile scores to counties for each region
# This script runs the aggregation for each region (south, west, east)

# Activate the Python environment
source loghub_env/bin/activate

# Set variables
COUNTY_SHP="/Users/yairtitelboim/Documents/Kernel/ALLAPPS/LOGhub/data/tl_2024_us_county/tl_2024_us_county.shp"

# Define regions
REGIONS=("south" "west" "east")

# Process each region
for REGION in "${REGIONS[@]}"; do
    echo "=========================================="
    echo "Processing region: $REGION"
    echo "=========================================="
    
    # Set region-specific variables
    TILE_SCORES="data/${REGION}/tile_scores.csv"
    OUTPUT="data/${REGION}/county_joined.geojson"
    
    # Check if tile scores file exists
    if [ ! -f "$TILE_SCORES" ]; then
        echo "Tile scores file not found: $TILE_SCORES"
        echo "Skipping region: $REGION"
        continue
    fi
    
    # Run aggregation script
    echo "Running aggregation script for $REGION region..."
    python tools/aggregate_tiles_to_counties.py \
      --tile-scores "$TILE_SCORES" \
      --county-shp "$COUNTY_SHP" \
      --output "$OUTPUT" \
      --visualize
    
    echo "$REGION region processing completed successfully!"
    echo ""
done

echo "Aggregation completed successfully for all regions!"
