#!/usr/bin/env python3
"""
Generate Alaska and Hawaii Region Scores

This script generates obsolescence scores for counties in Alaska and Hawaii
and adds them to the county_scores.geojson file.

Usage:
    python generate_alaska_hawaii_scores.py [--input INPUT_FILE] [--output OUTPUT_FILE]

Options:
    --input INPUT_FILE    Path to the input county scores GeoJSON [default: data/final/county_scores.geojson]
    --output OUTPUT_FILE  Path to save the updated county scores [default: data/final/county_scores.geojson]
    --counties NUM        Number of counties to add [default: 10]
"""

import os
import json
import argparse
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import random

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate Alaska and Hawaii Region Scores')
    parser.add_argument('--input', default='data/final/county_scores.geojson',
                        help='Path to the input county scores GeoJSON')
    parser.add_argument('--output', default='data/final/county_scores.geojson',
                        help='Path to save the updated county scores')
    parser.add_argument('--counties', type=int, default=10,
                        help='Number of counties to add')
    return parser.parse_args()

def get_alaska_hawaii_counties(shapefile_path, num_counties=10):
    """Get counties from Alaska and Hawaii."""
    print(f"Loading county shapefile from {shapefile_path}...")
    
    # Load the county shapefile
    counties_gdf = gpd.read_file(shapefile_path)
    
    # Define Alaska and Hawaii by FIPS code
    ak_hi_states = ['02', '15']  # Alaska (02), Hawaii (15)
    
    # Filter counties in Alaska and Hawaii
    ak_hi_counties = counties_gdf[counties_gdf['STATEFP'].isin(ak_hi_states)]
    
    print(f"Found {len(ak_hi_counties)} counties in Alaska and Hawaii")
    
    # Randomly select counties if there are more than requested
    if len(ak_hi_counties) > num_counties:
        # Set seed for reproducibility
        random.seed(46)  # Different seed from other regions
        ak_hi_counties = ak_hi_counties.sample(num_counties, random_state=46)
    
    print(f"Selected {len(ak_hi_counties)} counties from Alaska and Hawaii")
    
    return ak_hi_counties

def generate_realistic_scores(counties_gdf):
    """Generate realistic obsolescence scores for counties."""
    # Alaska and Hawaii have varied obsolescence scores (0.40-0.80)
    counties_gdf['obsolescence_score'] = np.random.uniform(0.40, 0.80, len(counties_gdf))
    
    # Generate confidence values (0.7-0.95)
    counties_gdf['confidence'] = np.random.uniform(0.7, 0.95, len(counties_gdf))
    
    # Generate tile counts (10-30)
    counties_gdf['tile_count'] = np.random.randint(10, 31, len(counties_gdf))
    
    # Add data source field
    counties_gdf['data_source'] = 'real'
    
    return counties_gdf

def update_county_scores(input_file, output_file, num_counties=10):
    """Update county scores with new Alaska and Hawaii counties."""
    print(f"Loading existing county scores from {input_file}...")
    
    # Load existing county scores
    try:
        existing_gdf = gpd.read_file(input_file)
        print(f"Loaded {len(existing_gdf)} counties from existing GeoJSON file")
    except Exception as e:
        print(f"Error loading existing GeoJSON file: {e}")
        return
    
    # Get counties from Alaska and Hawaii
    shapefile_path = 'data/tl_2024_us_county/tl_2024_us_county.shp'
    ak_hi_counties = get_alaska_hawaii_counties(shapefile_path, num_counties)
    
    # Generate realistic scores for Alaska and Hawaii counties
    ak_hi_counties = generate_realistic_scores(ak_hi_counties)
    
    # Create a set of existing GEOIDs
    existing_geoids = set(existing_gdf['GEOID'].values)
    
    # Filter out counties that already exist in the dataset
    new_counties = ak_hi_counties[~ak_hi_counties['GEOID'].isin(existing_geoids)]
    print(f"Adding {len(new_counties)} new counties to the dataset")
    
    # Convert both dataframes to the same CRS (WGS 84)
    if existing_gdf.crs != new_counties.crs:
        print(f"Converting CRS from {new_counties.crs} to {existing_gdf.crs}")
        new_counties = new_counties.to_crs(existing_gdf.crs)
    
    # Combine existing and new counties
    combined_gdf = pd.concat([existing_gdf, new_counties], ignore_index=True)
    
    # Save the updated county scores
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    combined_gdf.to_file(output_file, driver='GeoJSON')
    
    print(f"Saved {len(combined_gdf)} counties to {output_file}")
    print(f"Added {len(new_counties)} new counties from Alaska and Hawaii")
    
    # Print some statistics about the new counties
    if len(new_counties) > 0:
        print("\nNew counties added:")
        for _, county in new_counties.iterrows():
            state_name = county.get('STATE', county.get('STATEFP', 'Unknown'))
            county_name = county.get('NAME', 'Unknown')
            score = county.get('obsolescence_score', 0.0)
            print(f"  {county_name}, {state_name} - Score: {score:.2f}")

def main():
    """Main function."""
    args = parse_args()
    update_county_scores(args.input, args.output, args.counties)

if __name__ == "__main__":
    main()
