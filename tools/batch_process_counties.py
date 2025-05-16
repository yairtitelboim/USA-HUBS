#!/usr/bin/env python3
"""
Batch Process Counties

This script processes multiple counties one at a time using real satellite data.
It keeps track of which counties have been processed and which ones still need to be processed.

Usage:
    python batch_process_counties.py [--batch-size BATCH_SIZE] [--output OUTPUT_FILE]

Options:
    --batch-size BATCH_SIZE  Number of counties to process in this batch [default: 5]
    --output OUTPUT_FILE     Path to save the updated county scores [default: data/final/real_county_scores.geojson]
    --region REGION          Region to process (south, east, west, midwest, northeast, all) [default: all]
    --resume                 Resume from the last processed county
"""

import os
import argparse
import geopandas as gpd
import pandas as pd
import numpy as np
import subprocess
import time
import datetime
import logging
import sys
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/batch_processing.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Batch Process Counties')
    parser.add_argument('--batch-size', type=int, default=5,
                        help='Number of counties to process in this batch')
    parser.add_argument('--output', default='data/final/real_county_scores.geojson',
                        help='Path to save the updated county scores')
    parser.add_argument('--region', default='all',
                        choices=['south', 'east', 'west', 'midwest', 'northeast', 'all'],
                        help='Region to process')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from the last processed county')
    return parser.parse_args()

def get_region_states(region):
    """Get states in the specified region."""
    region_states = {
        'south': ['10', '12', '13', '24', '37', '45', '51', '11', '54',
                  '01', '21', '28', '47', '05', '22', '40', '48'],
        'east': ['09', '23', '25', '33', '44', '50', '34', '36', '42',
                 '10', '24', '51', '37', '45', '13', '12'],
        'west': ['04', '08', '16', '30', '32', '35', '49', '56',
                 '02', '06', '15', '41', '53'],
        'midwest': ['17', '18', '26', '39', '55', '19', '20', '27', '29', '31', '38', '46'],
        'northeast': ['09', '23', '25', '33', '44', '50', '34', '36', '42']
    }

    if region == 'all':
        # Combine all regions
        all_states = []
        for states in region_states.values():
            all_states.extend(states)
        return list(set(all_states))  # Remove duplicates

    return region_states.get(region, [])

def get_counties_to_process(region, output_file):
    """
    Get counties that need to be processed.

    Args:
        region: Region to process
        output_file: Path to the output file

    Returns:
        List of county FIPS codes to process
    """
    logger.info(f"Getting counties to process for region: {region}")

    try:
        # Load the county shapefile
        shapefile_path = 'data/tl_2024_us_county/tl_2024_us_county.shp'
        counties_gdf = gpd.read_file(shapefile_path)

        # Filter for the specified region if not 'all'
        if region != 'all':
            region_states = get_region_states(region)
            counties_gdf = counties_gdf[counties_gdf['STATEFP'].isin(region_states)]

        logger.info(f"Found {len(counties_gdf)} counties in the {region} region")

        # Get the list of county FIPS codes
        all_counties = counties_gdf['GEOID'].tolist()

        # Load existing county scores if the file exists
        processed_counties = []
        if os.path.exists(output_file):
            try:
                existing_gdf = gpd.read_file(output_file)
                logger.info(f"Loaded {len(existing_gdf)} counties from existing GeoJSON file")

                # Get the list of processed county FIPS codes
                if 'GEOID' in existing_gdf.columns:
                    processed_counties = existing_gdf['GEOID'].tolist()
            except Exception as e:
                logger.error(f"Error loading existing GeoJSON file: {e}")

        # Filter out counties that have already been processed
        counties_to_process = [c for c in all_counties if c not in processed_counties]

        logger.info(f"Found {len(counties_to_process)} counties to process")
        return counties_to_process

    except Exception as e:
        logger.error(f"Error getting counties to process: {e}")
        return []

def process_county(county_fips, output_file):
    """
    Process a single county.

    Args:
        county_fips: FIPS code of the county
        output_file: Path to the output file

    Returns:
        True if processing was successful, False otherwise
    """
    logger.info(f"Processing county {county_fips}...")

    try:
        # Run the process_real_satellite_only.py script
        command = (
            f"python tools/process_real_satellite_only.py "
            f"--county {county_fips} "
            f"--output {output_file}"
        )

        # Run the command
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)

        # Log the output
        logger.info(result.stdout)

        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing county {county_fips}: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def save_progress(counties_processed, counties_to_process):
    """
    Save progress to a file.

    Args:
        counties_processed: List of counties that have been processed
        counties_to_process: List of counties that still need to be processed
    """
    progress = {
        'processed': counties_processed,
        'to_process': counties_to_process,
        'last_updated': datetime.datetime.now().isoformat()
    }

    with open('logs/county_progress.json', 'w') as f:
        json.dump(progress, f, indent=2)

    logger.info(f"Saved progress: {len(counties_processed)} processed, {len(counties_to_process)} to go")

def load_progress():
    """
    Load progress from a file.

    Returns:
        Tuple of (counties_processed, counties_to_process)
    """
    if not os.path.exists('logs/county_progress.json'):
        return [], []

    try:
        with open('logs/county_progress.json', 'r') as f:
            progress = json.load(f)

        counties_processed = progress.get('processed', [])
        counties_to_process = progress.get('to_process', [])

        logger.info(f"Loaded progress: {len(counties_processed)} processed, {len(counties_to_process)} to go")
        return counties_processed, counties_to_process

    except Exception as e:
        logger.error(f"Error loading progress: {e}")
        return [], []

def main():
    """Main function to batch process counties."""
    args = parse_args()

    # Get counties to process
    if args.resume:
        logger.info("Resuming from last processed county...")
        counties_processed, counties_to_process = load_progress()

        if not counties_to_process:
            logger.info("No counties to process. Getting new counties...")
            counties_to_process = get_counties_to_process(args.region, args.output)
    else:
        counties_processed = []
        counties_to_process = get_counties_to_process(args.region, args.output)

    if not counties_to_process:
        logger.error("No counties to process. Exiting.")
        sys.exit(1)

    # Process counties in batches
    batch_size = min(args.batch_size, len(counties_to_process))
    logger.info(f"Processing {batch_size} counties in this batch...")

    # Process each county
    for i in range(batch_size):
        county_fips = counties_to_process[0]
        logger.info(f"Processing county {i+1}/{batch_size}: {county_fips}")

        # Process the county
        success = process_county(county_fips, args.output)

        if success:
            # Move the county from to_process to processed
            counties_processed.append(county_fips)
            counties_to_process.remove(county_fips)

            # Save progress
            save_progress(counties_processed, counties_to_process)
        else:
            logger.error(f"Failed to process county {county_fips}")

            # Move the county to the end of the list to try again later
            counties_to_process.remove(county_fips)
            counties_to_process.append(county_fips)

            # Save progress
            save_progress(counties_processed, counties_to_process)

    logger.info(f"Batch processing complete. Processed {batch_size} counties.")
    logger.info(f"Total counties processed: {len(counties_processed)}")
    logger.info(f"Counties remaining: {len(counties_to_process)}")

if __name__ == "__main__":
    main()
