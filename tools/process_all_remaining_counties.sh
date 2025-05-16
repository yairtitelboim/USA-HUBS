#!/bin/bash
# Process all remaining counties in batches
# This script will process all remaining counties in batches of 10
# It will run until all counties have been processed

# Set the output file
OUTPUT_FILE="data/final/fixed_county_scores.geojson"

# Set the batch size
BATCH_SIZE=10

# Set the maximum number of batches to process (set to a large number to process all)
MAX_BATCHES=100

# Function to get the number of remaining counties
get_remaining_count() {
    python -c "
import geopandas as gpd
import json

# Load the county shapefile to get total US counties
shapefile_path = 'data/tl_2024_us_county/tl_2024_us_county.shp'
counties_gdf = gpd.read_file(shapefile_path)
total_counties = len(counties_gdf)

# Load the fixed_county_scores.geojson to see how many we've processed
with open('$OUTPUT_FILE', 'r') as f:
    data = json.load(f)
processed_counties = len(data['features'])

# Get the FIPS codes of processed counties
processed_fips = set()
for feature in data['features']:
    if 'GEOID' in feature['properties']:
        processed_fips.add(feature['properties']['GEOID'])

# Get the FIPS codes of all counties
all_fips = set(counties_gdf['GEOID'].tolist())

# Calculate remaining counties
remaining_fips = all_fips - processed_fips
remaining_count = len(remaining_fips)

print(remaining_count)
"
}

# Process batches until all counties are processed or MAX_BATCHES is reached
batch_num=1
while [ $batch_num -le $MAX_BATCHES ]; do
    # Get the number of remaining counties
    remaining_count=$(get_remaining_count)
    
    # Check if there are any remaining counties
    if [ $remaining_count -eq 0 ]; then
        echo "All counties have been processed!"
        break
    fi
    
    echo "Batch $batch_num: Processing $BATCH_SIZE counties ($remaining_count remaining)"
    
    # Process a batch of counties
    python tools/process_remaining_counties.py --batch-size $BATCH_SIZE --output $OUTPUT_FILE
    
    # Check if the process was successful
    if [ $? -ne 0 ]; then
        echo "Error processing batch $batch_num"
        exit 1
    fi
    
    # Copy the updated file to the React app's public directory
    mkdir -p county-viz-app/public/data/final/
    cp $OUTPUT_FILE county-viz-app/public/data/final/
    
    echo "Batch $batch_num complete!"
    echo "Waiting 30 seconds before starting the next batch..."
    sleep 30
    
    # Increment the batch number
    batch_num=$((batch_num + 1))
done

echo "Processing complete!"
echo "Processed $(($MAX_BATCHES * $BATCH_SIZE)) counties in $((batch_num - 1)) batches"
