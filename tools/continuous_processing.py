#!/usr/bin/env python3
"""
Continuous Processing of Counties

This script continuously processes counties using real satellite data until a target percentage is reached.
It runs the batch_process_counties.py script in a loop, with a delay between batches to avoid rate limiting.

Usage:
    python continuous_processing.py [--target-percent TARGET_PERCENT] [--batch-size BATCH_SIZE] [--delay DELAY]

Options:
    --target-percent TARGET_PERCENT  Target percentage of counties to process [default: 95]
    --batch-size BATCH_SIZE          Number of counties to process in each batch [default: 5]
    --delay DELAY                    Delay in seconds between batches [default: 60]
    --output OUTPUT_FILE             Path to save the updated county scores [default: data/final/real_county_scores.geojson]
    --region REGION                  Region to process (south, east, west, midwest, northeast, all) [default: all]
"""

import os
import argparse
import subprocess
import time
import json
import geopandas as gpd
import logging
import sys
import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/continuous_processing.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Continuous Processing of Counties')
    parser.add_argument('--target-percent', type=float, default=95.0,
                        help='Target percentage of counties to process')
    parser.add_argument('--batch-size', type=int, default=5,
                        help='Number of counties to process in each batch')
    parser.add_argument('--delay', type=int, default=60,
                        help='Delay in seconds between batches')
    parser.add_argument('--output', default='data/final/real_county_scores.geojson',
                        help='Path to save the updated county scores')
    parser.add_argument('--region', default='all',
                        choices=['south', 'east', 'west', 'midwest', 'northeast', 'all'],
                        help='Region to process')
    return parser.parse_args()

def get_progress(output_file):
    """
    Get the current progress.
    
    Args:
        output_file: Path to the output file
        
    Returns:
        Tuple of (total_counties, processed_counties, percent_complete)
    """
    try:
        # Load the county shapefile to get the total number of counties
        shapefile_path = 'data/tl_2024_us_county/tl_2024_us_county.shp'
        counties_gdf = gpd.read_file(shapefile_path)
        total_counties = len(counties_gdf)
        
        # Load the output file to get the number of processed counties
        if os.path.exists(output_file):
            try:
                output_gdf = gpd.read_file(output_file)
                processed_counties = len(output_gdf)
            except Exception as e:
                logger.error(f"Error loading output file: {e}")
                processed_counties = 0
        else:
            processed_counties = 0
        
        # Calculate the percentage complete
        percent_complete = (processed_counties / total_counties) * 100
        
        return total_counties, processed_counties, percent_complete
    
    except Exception as e:
        logger.error(f"Error getting progress: {e}")
        return 0, 0, 0

def run_batch(batch_size, output_file, region):
    """
    Run a batch of county processing.
    
    Args:
        batch_size: Number of counties to process in the batch
        output_file: Path to the output file
        region: Region to process
        
    Returns:
        True if the batch was successful, False otherwise
    """
    try:
        # Run the batch_process_counties.py script
        command = (
            f"python tools/batch_process_counties.py "
            f"--batch-size {batch_size} "
            f"--region {region} "
            f"--output {output_file} "
            f"--resume"
        )
        
        # Run the command
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        
        # Log the output
        logger.info(result.stdout)
        
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running batch: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def main():
    """Main function to continuously process counties."""
    args = parse_args()
    
    logger.info(f"Starting continuous processing with target: {args.target_percent}%")
    logger.info(f"Batch size: {args.batch_size}, Delay: {args.delay} seconds")
    
    # Get initial progress
    total_counties, processed_counties, percent_complete = get_progress(args.output)
    logger.info(f"Initial progress: {processed_counties}/{total_counties} counties ({percent_complete:.1f}%)")
    
    # Continue processing until we reach the target percentage
    while percent_complete < args.target_percent:
        # Run a batch
        logger.info(f"Running batch with {args.batch_size} counties...")
        success = run_batch(args.batch_size, args.output, args.region)
        
        # Get updated progress
        total_counties, processed_counties, percent_complete = get_progress(args.output)
        logger.info(f"Current progress: {processed_counties}/{total_counties} counties ({percent_complete:.1f}%)")
        
        # Check if we've reached the target
        if percent_complete >= args.target_percent:
            logger.info(f"Target of {args.target_percent}% reached!")
            break
        
        # Delay before the next batch
        logger.info(f"Waiting {args.delay} seconds before the next batch...")
        time.sleep(args.delay)
    
    logger.info("Continuous processing complete!")
    logger.info(f"Final progress: {processed_counties}/{total_counties} counties ({percent_complete:.1f}%)")

if __name__ == "__main__":
    main()
