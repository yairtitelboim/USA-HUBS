#!/usr/bin/env python3
"""
Update Growth Potential Scores for All Counties

This script reads the existing fixed_county_scores.geojson file and updates the growth_potential_score
field for all counties based on their obsolescence scores. It handles the case where the file
might be being written to by the process_remaining_counties.py script.

Usage:
    python update_growth_scores.py [--input INPUT_FILE] [--output OUTPUT_FILE]

Options:
    --input INPUT_FILE    Path to the input GeoJSON file [default: data/final/fixed_county_scores.geojson]
    --output OUTPUT_FILE  Path to save the updated GeoJSON file [default: data/final/fixed_county_scores.geojson]
"""

import os
import sys
import argparse
import geopandas as gpd
import numpy as np
import logging
import time
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/update_growth_scores.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Update Growth Potential Scores for All Counties')
    parser.add_argument('--input', default='data/final/fixed_county_scores.geojson',
                        help='Path to the input GeoJSON file')
    parser.add_argument('--output', default='data/final/fixed_county_scores.geojson',
                        help='Path to save the updated GeoJSON file')
    parser.add_argument('--react-app-dir', default='county-viz-app/public/data/final/',
                        help='Path to the React app public directory')
    return parser.parse_args()

def calculate_growth_score(obsolescence_score):
    """
    Calculate growth potential score based on obsolescence score.

    Args:
        obsolescence_score: Obsolescence score between 0 and 1

    Returns:
        Growth potential score between 0 and 1
    """
    # Estimate the raw indices with increased baseline NDVI
    ndvi_value = 0.5  # Increased baseline NDVI value (was 0.4)
    ndbi_value = (3 * obsolescence_score - 1 + ndvi_value) / 2  # Derived from obsolescence formula
    bsi_value = ndbi_value  # Assume similar to NDBI for simplicity

    # Ensure values are in reasonable ranges
    ndbi_value = max(-1, min(1, ndbi_value))
    bsi_value = max(-1, min(1, bsi_value))

    # Calibrated formula for growth potential:
    # - Uses negative offset (-0.1) for NDBI to shift distribution down
    # - Applies scaling factor (1.2) to spread out the distribution
    # - Maintains original relationship direction but with better calibration
    base_score = 0.5 * (ndbi_value - (-0.1)) + 0.3 * (ndvi_value - 0.2) + 0.2 * bsi_value
    scaled_score = base_score * 1.2

    # Clamp to 0-1 range
    growth_score = max(0, min(1, scaled_score))
    return growth_score

def update_growth_scores(input_file, output_file, react_app_dir):
    """
    Update growth potential scores for all counties.

    Args:
        input_file: Path to the input GeoJSON file
        output_file: Path to save the updated GeoJSON file
        react_app_dir: Path to the React app public directory

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Updating growth potential scores in {input_file}")

    try:
        # Load the GeoJSON file
        counties_gdf = gpd.read_file(input_file)
        logger.info(f"Loaded {len(counties_gdf)} counties from {input_file}")

        # Create a backup of the original file
        backup_file = input_file + '.bak'
        counties_gdf.to_file(backup_file, driver='GeoJSON')
        logger.info(f"Created backup of original file at {backup_file}")

        # Initialize growth_potential_score column if it doesn't exist
        if 'growth_potential_score' not in counties_gdf.columns:
            counties_gdf['growth_potential_score'] = np.nan
            logger.info("Added growth_potential_score column")

        # Count counties with and without growth potential scores
        counties_with_growth = counties_gdf['growth_potential_score'].notna().sum()
        counties_without_growth = counties_gdf['growth_potential_score'].isna().sum()
        logger.info(f"Counties with growth potential scores: {counties_with_growth}")
        logger.info(f"Counties without growth potential scores: {counties_without_growth}")

        # Update growth potential scores for all counties
        logger.info("Updating growth potential scores for all counties")

        # Process each county
        for idx, county in tqdm(counties_gdf.iterrows(), total=len(counties_gdf), desc="Processing counties"):
            # Get the obsolescence score
            obsolescence_score = county['obsolescence_score']

            # Calculate growth potential score
            growth_score = calculate_growth_score(obsolescence_score)

            # Store the value
            counties_gdf.at[idx, 'growth_potential_score'] = growth_score

        # Save the updated GeoJSON file
        counties_gdf.to_file(output_file, driver='GeoJSON')
        logger.info(f"Saved {len(counties_gdf)} counties with updated growth potential scores to {output_file}")

        # Copy to React app directory
        if react_app_dir:
            os.makedirs(react_app_dir, exist_ok=True)
            react_file = os.path.join(react_app_dir, os.path.basename(output_file))
            counties_gdf.to_file(react_file, driver='GeoJSON')
            logger.info(f"Copied updated file to React app directory: {react_file}")

        return True

    except Exception as e:
        logger.error(f"Error updating growth potential scores: {e}")
        return False

def main():
    """Main function to update growth potential scores for all counties."""
    args = parse_args()

    logger.info("Starting to update growth potential scores")

    # Try to update growth potential scores, with retries if the file is being written to
    max_retries = 5
    retry_delay = 30  # seconds

    for retry in range(max_retries):
        try:
            if update_growth_scores(args.input, args.output, args.react_app_dir):
                logger.info("Successfully updated growth potential scores")
                break
            else:
                logger.error(f"Failed to update growth potential scores (attempt {retry+1}/{max_retries})")
                if retry < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Error in update process: {e}")
            if retry < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
    else:
        logger.error(f"Failed to update growth potential scores after {max_retries} attempts")
        sys.exit(1)

    logger.info("Process completed successfully")

if __name__ == "__main__":
    main()
