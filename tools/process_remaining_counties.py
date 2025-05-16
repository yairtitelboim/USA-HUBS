#!/usr/bin/env python3
"""
Process Remaining Counties with Real Satellite Data

This script processes the remaining counties that haven't been processed yet
with real satellite data. It uses the process_real_satellite_only.py script
to process each county and updates the fixed_county_scores.geojson file.

Usage:
    python process_remaining_counties.py [--batch-size BATCH_SIZE] [--output OUTPUT_FILE]

Options:
    --batch-size BATCH_SIZE   Number of counties to process in this batch [default: 10]
    --output OUTPUT_FILE      Path to save the updated county scores [default: data/final/fixed_county_scores.geojson]
    --service-account-key     Path to Google Earth Engine service account key [default: config/gee/gentle-cinema-458613-f3-51d8ea2711e7.json]
"""

import os
import argparse
import geopandas as gpd
import json
import subprocess
import time
import datetime
import logging
import sys
import random
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/remaining_counties_processing.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process Remaining Counties with Real Satellite Data')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Number of counties to process in this batch')
    parser.add_argument('--output', default='data/final/fixed_county_scores.geojson',
                        help='Path to save the updated county scores')
    parser.add_argument('--service-account-key',
                        default='config/gee/gentle-cinema-458613-f3-51d8ea2711e7.json',
                        help='Path to Google Earth Engine service account key')
    parser.add_argument('--start-date', default='2023-01-01',
                        help='Start date for satellite imagery (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2023-12-31',
                        help='End date for satellite imagery (YYYY-MM-DD)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for county selection')
    return parser.parse_args()

def get_remaining_counties(processed_file, shapefile_path):
    """
    Get the list of counties that haven't been processed yet.

    Args:
        processed_file: Path to the file with processed counties
        shapefile_path: Path to the county shapefile

    Returns:
        List of FIPS codes for counties that haven't been processed yet
    """
    logger.info("Identifying remaining counties to process...")

    try:
        # Load the county shapefile to get all US counties
        counties_gdf = gpd.read_file(shapefile_path)
        all_fips = set(counties_gdf['GEOID'].tolist())
        logger.info(f"Found {len(all_fips)} total counties in shapefile")

        # Load the processed counties
        if os.path.exists(processed_file):
            with open(processed_file, 'r') as f:
                data = json.load(f)
            
            # Get the FIPS codes of processed counties
            processed_fips = set()
            for feature in data['features']:
                if 'GEOID' in feature['properties']:
                    processed_fips.add(feature['properties']['GEOID'])
            
            logger.info(f"Found {len(processed_fips)} processed counties")
        else:
            logger.warning(f"Processed file {processed_file} not found, assuming no counties processed yet")
            processed_fips = set()

        # Calculate remaining counties
        remaining_fips = list(all_fips - processed_fips)
        logger.info(f"Found {len(remaining_fips)} remaining counties to process")

        return remaining_fips

    except Exception as e:
        logger.error(f"Error getting remaining counties: {e}")
        return []

def process_county(county_fips, output_file, service_account_key, start_date, end_date):
    """
    Process a single county with real satellite data.

    Args:
        county_fips: FIPS code of the county to process
        output_file: Path to save the updated county scores
        service_account_key: Path to Google Earth Engine service account key
        start_date: Start date for satellite imagery
        end_date: End date for satellite imagery

    Returns:
        True if processing was successful, False otherwise
    """
    logger.info(f"Processing county {county_fips}...")
    
    # Build the command
    command = [
        "python", "tools/process_real_satellite_only.py",
        "--county", county_fips,
        "--output", output_file,
        "--start-date", start_date,
        "--end-date", end_date
    ]
    
    if service_account_key:
        command.extend(["--service-account-key", service_account_key])
    
    # Run the command
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info(f"Successfully processed county {county_fips}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing county {county_fips}: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def process_batch(county_batch, output_file, service_account_key, start_date, end_date):
    """
    Process a batch of counties with real satellite data.

    Args:
        county_batch: List of county FIPS codes to process
        output_file: Path to save the updated county scores
        service_account_key: Path to Google Earth Engine service account key
        start_date: Start date for satellite imagery
        end_date: End date for satellite imagery

    Returns:
        Number of successfully processed counties
    """
    logger.info(f"Processing batch of {len(county_batch)} counties...")
    
    success_count = 0
    for i, county_fips in enumerate(county_batch):
        logger.info(f"Processing county {i+1}/{len(county_batch)}: {county_fips}")
        
        # Process the county
        success = process_county(county_fips, output_file, service_account_key, start_date, end_date)
        
        # Update success count
        if success:
            success_count += 1
            logger.info(f"Successfully processed county {county_fips}")
        else:
            logger.warning(f"Failed to process county {county_fips}")
        
        # Add a small delay between counties to avoid rate limiting
        if i < len(county_batch) - 1:
            logger.info("Waiting 5 seconds before processing the next county...")
            time.sleep(5)
    
    return success_count

def copy_to_react_app(output_file):
    """
    Copy the output file to the React app's public directory.

    Args:
        output_file: Path to the output file

    Returns:
        True if copy was successful, False otherwise
    """
    logger.info("Copying to React app's public directory...")
    
    try:
        react_dir = "county-viz-app/public/data/final/"
        os.makedirs(react_dir, exist_ok=True)
        
        react_file = os.path.join(react_dir, os.path.basename(output_file))
        subprocess.run(["cp", output_file, react_file], check=True)
        
        logger.info(f"Successfully copied to {react_file}")
        return True
    except Exception as e:
        logger.error(f"Error copying to React app: {e}")
        return False

def main():
    """Main function."""
    args = parse_args()
    
    # Set random seed
    random.seed(args.seed)
    
    # Get the list of remaining counties
    shapefile_path = 'data/tl_2024_us_county/tl_2024_us_county.shp'
    remaining_counties = get_remaining_counties(args.output, shapefile_path)
    
    if not remaining_counties:
        logger.info("No remaining counties to process!")
        return 0
    
    # Shuffle the list to process counties from different regions
    random.shuffle(remaining_counties)
    
    # Select a batch of counties to process
    batch_size = min(args.batch_size, len(remaining_counties))
    county_batch = remaining_counties[:batch_size]
    
    logger.info(f"Selected {batch_size} counties to process in this batch")
    logger.info(f"County FIPS codes: {county_batch}")
    
    # Process the batch
    success_count = process_batch(
        county_batch, args.output, args.service_account_key, args.start_date, args.end_date
    )
    
    # Copy to React app
    copy_to_react_app(args.output)
    
    # Print summary
    logger.info(f"Batch processing complete!")
    logger.info(f"Successfully processed {success_count}/{batch_size} counties")
    logger.info(f"Remaining counties: {len(remaining_counties) - batch_size}")
    
    return 0 if success_count == batch_size else 1

if __name__ == "__main__":
    sys.exit(main())
