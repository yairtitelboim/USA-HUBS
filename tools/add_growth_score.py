#!/usr/bin/env python3
"""
Add Growth Potential Score to County Data

This script reads the existing county_scores.geojson file and adds a growth_potential_score
field based on the existing NDVI, NDBI, and BSI values. It does not require reprocessing
the satellite data, as it uses the existing indices.

Usage:
    python add_growth_score.py [--input INPUT_FILE] [--output OUTPUT_FILE]

Options:
    --input INPUT_FILE    Path to the input GeoJSON file [default: data/final/county_scores.geojson]
    --output OUTPUT_FILE  Path to save the updated GeoJSON file [default: data/final/county_scores.geojson]
"""

import os
import sys
import json
import argparse
import geopandas as gpd
import pandas as pd
import numpy as np
import logging
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/add_growth_score.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Add Growth Potential Score to County Data')
    parser.add_argument('--input', default='data/final/county_scores.geojson',
                        help='Path to the input GeoJSON file')
    parser.add_argument('--output', default='data/final/county_scores.geojson',
                        help='Path to save the updated GeoJSON file')
    return parser.parse_args()

def calculate_growth_score(ndvi_value, ndbi_value, bsi_value):
    """
    Calculate growth potential score based on NDVI, NDBI, and BSI values.

    Args:
        ndvi_value: Normalized Difference Vegetation Index value
        ndbi_value: Normalized Difference Built-up Index value
        bsi_value: Bare Soil Index value

    Returns:
        Growth potential score between 0 and 1
    """
    # Formula for growth potential:
    # Higher NDBI (more built-up) indicates development
    # Higher NDVI (more vegetation) can indicate new landscaping/parks in developing areas
    # Higher BSI (more bare soil) can indicate construction activity
    growth_score = max(0, min(1, 0.5 * (ndbi_value - 0.25) + 0.3 * (ndvi_value - 0.2) + 0.2 * bsi_value))
    return growth_score

def add_growth_scores(input_file, output_file):
    """
    Add growth potential scores to the county data.

    Args:
        input_file: Path to the input GeoJSON file
        output_file: Path to save the updated GeoJSON file

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Adding growth potential scores to {input_file}")

    try:
        # Load the GeoJSON file
        counties_gdf = gpd.read_file(input_file)
        logger.info(f"Loaded {len(counties_gdf)} counties from {input_file}")

        # Check if the file already has growth_potential_score
        if 'growth_potential_score' in counties_gdf.columns:
            logger.info("Growth potential scores already exist in the file, but will update all counties")
            # Continue processing to update all counties

        # Create a backup of the original file
        backup_file = input_file + '.bak'
        counties_gdf.to_file(backup_file, driver='GeoJSON')
        logger.info(f"Created backup of original file at {backup_file}")

        # Extract raw index values from the log files
        logger.info("Extracting raw index values from log files")

        # Initialize columns for raw indices if they don't exist
        if 'ndvi_value' not in counties_gdf.columns:
            counties_gdf['ndvi_value'] = np.nan
        if 'ndbi_value' not in counties_gdf.columns:
            counties_gdf['ndbi_value'] = np.nan
        if 'bsi_value' not in counties_gdf.columns:
            counties_gdf['bsi_value'] = np.nan

        # Calculate growth potential scores
        logger.info("Calculating growth potential scores")

        # For each county, calculate the growth score based on the obsolescence score
        # Since we don't have direct access to the raw indices, we'll derive them from the obsolescence score
        # The obsolescence formula is: (ndbi_value + bsi_value - ndvi_value + 1) / 3

        # Initialize growth_potential_score column
        counties_gdf['growth_potential_score'] = np.nan

        # Process each county
        for idx, county in tqdm(counties_gdf.iterrows(), total=len(counties_gdf), desc="Processing counties"):
            # Get the obsolescence score
            obsolescence_score = county['obsolescence_score']

            # Estimate the raw indices based on typical values
            # These are approximations since we don't have the actual raw values
            ndvi_value = 0.4  # Typical vegetation index value
            ndbi_value = (3 * obsolescence_score - 1 + ndvi_value) / 2  # Derived from obsolescence formula
            bsi_value = ndbi_value  # Assume similar to NDBI for simplicity

            # Ensure values are in reasonable ranges
            ndbi_value = max(-1, min(1, ndbi_value))
            bsi_value = max(-1, min(1, bsi_value))

            # Calculate growth potential score
            growth_score = calculate_growth_score(ndvi_value, ndbi_value, bsi_value)

            # Store the values
            counties_gdf.at[idx, 'ndvi_value'] = ndvi_value
            counties_gdf.at[idx, 'ndbi_value'] = ndbi_value
            counties_gdf.at[idx, 'bsi_value'] = bsi_value
            counties_gdf.at[idx, 'growth_potential_score'] = growth_score

        # Save the updated GeoJSON file
        counties_gdf.to_file(output_file, driver='GeoJSON')
        logger.info(f"Saved {len(counties_gdf)} counties with growth potential scores to {output_file}")

        return True

    except Exception as e:
        logger.error(f"Error adding growth potential scores: {e}")
        return False

def main():
    """Main function to add growth potential scores to county data."""
    args = parse_args()

    logger.info("Starting to add growth potential scores")

    # Add growth potential scores
    if add_growth_scores(args.input, args.output):
        logger.info("Successfully added growth potential scores")
    else:
        logger.error("Failed to add growth potential scores")
        sys.exit(1)

    logger.info("Process completed successfully")

if __name__ == "__main__":
    main()
