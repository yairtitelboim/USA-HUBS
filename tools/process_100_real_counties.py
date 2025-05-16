#!/usr/bin/env python3
"""
Process 100 counties using only real satellite data.
No fallbacks, no simulations, no sample data.
"""

import os
import sys
import argparse
import geopandas as gpd
import pandas as pd
import datetime
import logging
import subprocess
import time
import random
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/real_satellite_processing.log')
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process 100 counties using only real satellite data.')
    parser.add_argument('--output', type=str, default='data/final/real_county_scores.geojson',
                        help='Path to the output GeoJSON file')
    parser.add_argument('--service-account-key', type=str, 
                        default='config/gee/gentle-cinema-458613-f3-51d8ea2711e7.json',
                        help='Path to the Google Earth Engine service account key')
    parser.add_argument('--region', type=str, choices=['west', 'midwest', 'south', 'northeast', 'all'],
                        default='all', help='Region to process')
    parser.add_argument('--start-date', type=str, default='2023-01-01',
                        help='Start date for satellite imagery (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2023-12-31',
                        help='End date for satellite imagery (YYYY-MM-DD)')
    return parser.parse_args()

def get_counties_to_process(region, output_file):
    """
    Get a list of counties to process.
    
    Args:
        region: Region to process (west, midwest, south, northeast, all)
        output_file: Path to the output file
        
    Returns:
        List of county FIPS codes to process
    """
    logger.info(f"Getting counties to process for region: {region}")
    
    # Load the county shapefile
    counties = gpd.read_file('data/tl_2024_us_county/tl_2024_us_county.shp')
    
    # Filter by region if specified
    if region != 'all':
        # Define regions based on state FIPS codes
        regions = {
            'west': ['02', '04', '06', '08', '15', '16', '30', '32', '35', '41', '49', '53', '56'],
            'midwest': ['17', '18', '19', '20', '26', '27', '29', '31', '38', '39', '46', '55'],
            'south': ['01', '05', '10', '11', '12', '13', '21', '22', '24', '28', '37', '40', '45', '47', '48', '51', '54'],
            'northeast': ['09', '23', '25', '33', '34', '36', '42', '44', '50']
        }
        
        # Filter counties by region
        counties = counties[counties['STATEFP'].isin(regions[region])]
        
    logger.info(f"Found {len(counties)} counties in the {region} region")
    
    # Load existing counties if the file exists
    existing_counties = set()
    if os.path.exists(output_file):
        try:
            existing_gdf = gpd.read_file(output_file)
            logger.info(f"Loaded {len(existing_gdf)} counties from existing GeoJSON file")
            
            # Create a set of existing GEOIDs
            if 'GEOID' in existing_gdf.columns:
                existing_counties = set(existing_gdf['GEOID'].values)
        except Exception as e:
            logger.error(f"Error loading existing GeoJSON file: {e}")
    
    # Filter out counties that have already been processed
    counties_to_process = counties[~counties['GEOID'].isin(existing_counties)]
    logger.info(f"Found {len(counties_to_process)} counties to process")
    
    # Get the FIPS codes
    fips_codes = counties_to_process['GEOID'].tolist()
    
    # Shuffle the list to get a random sample
    random.shuffle(fips_codes)
    
    # Return the first 100 counties (or all if less than 100)
    return fips_codes[:100]

def process_county(county_fips, output_file, service_account_key, start_date, end_date):
    """
    Process a single county using the process_real_satellite_only.py script.
    
    Args:
        county_fips: County FIPS code
        output_file: Path to the output file
        service_account_key: Path to the Google Earth Engine service account key
        start_date: Start date for satellite imagery
        end_date: End date for satellite imagery
        
    Returns:
        True if processing was successful, False otherwise
    """
    logger.info(f"Processing county {county_fips}...")
    
    # Build the command
    cmd = [
        'python', 'tools/process_real_satellite_only.py',
        '--county', county_fips,
        '--output', output_file,
        '--service-account-key', service_account_key,
        '--start-date', start_date,
        '--end-date', end_date
    ]
    
    # Run the command
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing county {county_fips}: {e}")
        logger.error(e.stdout)
        logger.error(e.stderr)
        return False

def main():
    """Main function to process 100 counties."""
    args = parse_args()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Get counties to process
    counties = get_counties_to_process(args.region, args.output)
    
    # Limit to 100 counties
    counties = counties[:100]
    
    # Process counties
    logger.info(f"Processing {len(counties)} counties...")
    
    # Track progress
    successful = 0
    failed = 0
    
    # Process each county with a progress bar
    for i, county in enumerate(tqdm(counties, desc="Processing counties")):
        # Calculate estimated time remaining
        if i > 0:
            elapsed_time = time.time() - start_time
            avg_time_per_county = elapsed_time / i
            remaining_counties = len(counties) - i
            estimated_time_remaining = avg_time_per_county * remaining_counties
            
            # Format as hours, minutes, seconds
            hours, remainder = divmod(estimated_time_remaining, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            logger.info(f"Processing county {i+1}/{len(counties)} - Estimated time remaining: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        else:
            # Start timing
            start_time = time.time()
            logger.info(f"Processing county {i+1}/{len(counties)}")
        
        # Process the county
        if process_county(county, args.output, args.service_account_key, args.start_date, args.end_date):
            successful += 1
        else:
            failed += 1
        
        # Log progress
        logger.info(f"Progress: {i+1}/{len(counties)} counties processed ({successful} successful, {failed} failed)")
        
        # Calculate completion percentage
        completion_percentage = (i + 1) / len(counties) * 100
        logger.info(f"Completion: {completion_percentage:.1f}%")
    
    # Log final results
    logger.info(f"Processing complete. {successful} counties processed successfully, {failed} counties failed.")

if __name__ == "__main__":
    main()
