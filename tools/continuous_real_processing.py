#!/usr/bin/env python3
"""
Continuous processing of counties with real satellite data until reaching a target count.
Monitors data quality and provides detailed progress reports.
"""

import os
import sys
import argparse
import time
import random
import json
import geopandas as gpd
import pandas as pd
import datetime
import logging
import subprocess
import numpy as np
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/continuous_processing.log')
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process counties with real satellite data until reaching a target count.')
    parser.add_argument('--output', type=str, default='data/final/real_county_scores.geojson',
                        help='Path to the output GeoJSON file')
    parser.add_argument('--service-account-key', type=str,
                        default='config/gee/gentle-cinema-458613-f3-51d8ea2711e7.json',
                        help='Path to the Google Earth Engine service account key')
    parser.add_argument('--target-count', type=int, default=1000,
                        help='Target number of counties to process')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Number of counties to process in each batch')
    parser.add_argument('--delay', type=int, default=60,
                        help='Delay in seconds between batches')
    parser.add_argument('--start-date', type=str, default='2023-01-01',
                        help='Start date for satellite imagery (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2023-12-31',
                        help='End date for satellite imagery (YYYY-MM-DD)')
    return parser.parse_args()

def get_counties_to_process(output_file, batch_size):
    """
    Get a list of counties to process.

    Args:
        output_file: Path to the output file
        batch_size: Number of counties to process

    Returns:
        List of county FIPS codes to process
    """
    logger.info(f"Getting counties to process (batch size: {batch_size})")

    # Load the county shapefile
    counties = gpd.read_file('data/tl_2024_us_county/tl_2024_us_county.shp')
    logger.info(f"Found {len(counties)} counties in the shapefile")

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

    # Return the first batch_size counties (or all if less than batch_size)
    return fips_codes[:batch_size]

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

def analyze_data_quality(output_file):
    """
    Analyze the quality of the data in the output file.

    Args:
        output_file: Path to the output file

    Returns:
        Dictionary with quality metrics
    """
    logger.info(f"Analyzing data quality in {output_file}...")

    try:
        # Load the data
        data = json.load(open(output_file))

        # Extract scores
        scores = [f['properties']['obsolescence_score'] for f in data['features']]
        confidences = [f['properties']['confidence'] for f in data['features']]
        tile_counts = [f['properties']['tile_count'] for f in data['features']]

        # Calculate metrics
        metrics = {
            'total_counties': len(data['features']),
            'avg_score': np.mean(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'median_score': np.median(scores),
            'avg_confidence': np.mean(confidences),
            'avg_tile_count': np.mean(tile_counts),
            'min_tile_count': min(tile_counts),
            'max_tile_count': max(tile_counts)
        }

        # Log the metrics
        logger.info(f"Data quality metrics:")
        logger.info(f"  Total counties: {metrics['total_counties']}")
        logger.info(f"  Average score: {metrics['avg_score']:.2f}")
        logger.info(f"  Score range: {metrics['min_score']:.2f} - {metrics['max_score']:.2f}")
        logger.info(f"  Median score: {metrics['median_score']:.2f}")
        logger.info(f"  Average confidence: {metrics['avg_confidence']:.2f}")
        logger.info(f"  Average tile count: {metrics['avg_tile_count']:.1f}")
        logger.info(f"  Tile count range: {metrics['min_tile_count']} - {metrics['max_tile_count']}")

        return metrics
    except Exception as e:
        logger.error(f"Error analyzing data quality: {e}")
        return None

def main():
    """Main function to continuously process counties until reaching the target count."""
    args = parse_args()

    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Initialize counters
    total_processed = 0
    total_successful = 0
    total_failed = 0

    # Start time for the entire process
    start_time_total = time.time()

    # Check if the output file exists
    if os.path.exists(args.output):
        try:
            existing_data = json.load(open(args.output))
            current_count = len(existing_data['features'])
            logger.info(f"Found existing output file with {current_count} counties")
        except Exception as e:
            logger.error(f"Error loading existing output file: {e}")
            current_count = 0
    else:
        current_count = 0

    # Main processing loop
    while current_count < args.target_count:
        logger.info(f"Starting batch processing ({current_count}/{args.target_count} counties processed so far)")

        # Get counties to process
        counties = get_counties_to_process(args.output, args.batch_size)

        if not counties:
            logger.info("No more counties to process")
            break

        # Process counties in this batch
        batch_successful = 0
        batch_failed = 0

        # Start time for this batch
        start_time_batch = time.time()

        # Process each county with a progress bar
        for i, county in enumerate(tqdm(counties, desc="Processing counties")):
            # Calculate estimated time remaining for this batch
            if i > 0:
                elapsed_time = time.time() - start_time_batch
                avg_time_per_county = elapsed_time / i
                remaining_counties = len(counties) - i
                estimated_time_remaining = avg_time_per_county * remaining_counties

                # Format as hours, minutes, seconds
                hours, remainder = divmod(estimated_time_remaining, 3600)
                minutes, seconds = divmod(remainder, 60)

                logger.info(f"Processing county {i+1}/{len(counties)} in current batch - Estimated time remaining for batch: {int(hours)}h {int(minutes)}m {int(seconds)}s")
            else:
                logger.info(f"Processing county {i+1}/{len(counties)} in current batch")

            # Process the county
            if process_county(county, args.output, args.service_account_key, args.start_date, args.end_date):
                batch_successful += 1
                total_successful += 1
            else:
                batch_failed += 1
                total_failed += 1

            total_processed += 1

            # Update current count
            if os.path.exists(args.output):
                try:
                    existing_data = json.load(open(args.output))
                    current_count = len(existing_data['features'])
                except Exception as e:
                    logger.error(f"Error loading output file: {e}")

            # Check if we've reached the target
            if current_count >= args.target_count:
                logger.info(f"Reached target count of {args.target_count} counties")
                break

        # Calculate batch statistics
        batch_elapsed_time = time.time() - start_time_batch
        batch_avg_time_per_county = batch_elapsed_time / len(counties) if counties else 0

        logger.info(f"Batch completed: {batch_successful} successful, {batch_failed} failed")
        logger.info(f"Batch processing time: {batch_elapsed_time:.1f} seconds ({batch_avg_time_per_county:.1f} seconds per county)")

        # Analyze data quality
        analyze_data_quality(args.output)

        # Calculate overall progress
        total_elapsed_time = time.time() - start_time_total
        counties_remaining = args.target_count - current_count

        if total_processed > 0:
            avg_time_per_county = total_elapsed_time / total_processed
            estimated_time_remaining = avg_time_per_county * counties_remaining

            # Format as hours, minutes, seconds
            hours, remainder = divmod(estimated_time_remaining, 3600)
            minutes, seconds = divmod(remainder, 60)

            logger.info(f"Overall progress: {current_count}/{args.target_count} counties processed ({current_count/args.target_count*100:.1f}%)")
            logger.info(f"Estimated time remaining: {int(hours)}h {int(minutes)}m {int(seconds)}s")

        # Delay before next batch
        if current_count < args.target_count:
            logger.info(f"Waiting {args.delay} seconds before next batch...")
            time.sleep(args.delay)

    # Final statistics
    total_elapsed_time = time.time() - start_time_total
    hours, remainder = divmod(total_elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    logger.info(f"Processing complete: {total_successful} successful, {total_failed} failed")
    logger.info(f"Total processing time: {int(hours)}h {int(minutes)}m {int(seconds)}s")

    # Final data quality analysis
    analyze_data_quality(args.output)

if __name__ == "__main__":
    main()
