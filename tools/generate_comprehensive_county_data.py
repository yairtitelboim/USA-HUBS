#!/usr/bin/env python3
"""
Generate Comprehensive County Data

This script generates a comprehensive county dataset with realistic obsolescence scores
for all US counties by combining the existing county_scores.geojson with the full US
county shapefile.

Usage:
    python generate_comprehensive_county_data.py [--input INPUT_FILE] [--shapefile SHAPEFILE] [--output OUTPUT_FILE]

Options:
    --input INPUT_FILE      Path to the existing county scores GeoJSON [default: data/final/county_scores.geojson]
    --shapefile SHAPEFILE   Path to the US county shapefile [default: data/tl_2024_us_county/tl_2024_us_county.shp]
    --output OUTPUT_FILE    Path to save the comprehensive county scores [default: data/final/comprehensive_county_scores.geojson]
    --regional              Generate scores with regional patterns
    --seed SEED             Random seed for reproducibility [default: 42]
"""

import os
import json
import argparse
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate comprehensive county data')
    parser.add_argument('--input', default='data/final/county_scores.geojson',
                        help='Path to the existing county scores GeoJSON')
    parser.add_argument('--shapefile', default='data/tl_2024_us_county/tl_2024_us_county.shp',
                        help='Path to the US county shapefile')
    parser.add_argument('--output', default='data/final/comprehensive_county_scores.geojson',
                        help='Path to save the comprehensive county scores')
    parser.add_argument('--regional', action='store_true',
                        help='Generate scores with regional patterns')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility')
    return parser.parse_args()

def get_region(state_fips):
    """Determine the region based on state FIPS code."""
    # Northeast: CT, ME, MA, NH, RI, VT, NJ, NY, PA
    northeast = ['09', '23', '25', '33', '44', '50', '34', '36', '42']
    # Midwest: IL, IN, MI, OH, WI, IA, KS, MN, MO, NE, ND, SD
    midwest = ['17', '18', '26', '39', '55', '19', '20', '27', '29', '31', '38', '46']
    # South: DE, FL, GA, MD, NC, SC, VA, DC, WV, AL, KY, MS, TN, AR, LA, OK, TX
    south = ['10', '12', '13', '24', '37', '45', '51', '11', '54', '01', '21', '28', '47', '05', '22', '40', '48']
    # West: AZ, CO, ID, MT, NV, NM, UT, WY, AK, CA, HI, OR, WA
    west = ['04', '08', '16', '30', '32', '35', '49', '56', '02', '06', '15', '41', '53']
    
    if state_fips in northeast:
        return 'Northeast'
    elif state_fips in midwest:
        return 'Midwest'
    elif state_fips in south:
        return 'South'
    elif state_fips in west:
        return 'West'
    else:
        return 'Unknown'

def generate_regional_score(region, base_score=None):
    """Generate a score based on the region."""
    # Define regional biases
    regional_bias = {
        'Northeast': {'mean': 0.45, 'std': 0.15},
        'Midwest': {'mean': 0.55, 'std': 0.18},
        'South': {'mean': 0.75, 'std': 0.20},
        'West': {'mean': 0.65, 'std': 0.22},
        'Unknown': {'mean': 0.50, 'std': 0.25}
    }
    
    # If we have a base score, adjust it slightly
    if base_score is not None:
        # Add some noise but keep it within the regional pattern
        noise = np.random.normal(0, 0.1)
        score = base_score + noise
        # Ensure it's within bounds
        return max(0.01, min(0.99, score))
    
    # Otherwise generate from the regional distribution
    bias = regional_bias[region]
    score = np.random.normal(bias['mean'], bias['std'])
    # Ensure it's within bounds
    return max(0.01, min(0.99, score))

def generate_comprehensive_county_data(input_file, shapefile, output_file, regional=False, seed=42):
    """Generate comprehensive county data."""
    # Set random seed for reproducibility
    np.random.seed(seed)
    
    print(f"Loading existing county data from {input_file}...")
    try:
        existing_gdf = gpd.read_file(input_file)
        print(f"Loaded {len(existing_gdf)} counties with existing scores")
    except Exception as e:
        print(f"Error loading existing GeoJSON: {e}")
        existing_gdf = gpd.GeoDataFrame()
    
    print(f"Loading county shapefile from {shapefile}...")
    try:
        counties_gdf = gpd.read_file(shapefile)
        print(f"Loaded {len(counties_gdf)} counties from shapefile")
    except Exception as e:
        print(f"Error loading shapefile: {e}")
        return
    
    # Create a mapping of existing county data
    existing_data = {}
    if not existing_gdf.empty:
        for _, row in existing_gdf.iterrows():
            if 'GEOID' in row:
                geoid = row['GEOID']
                existing_data[geoid] = {
                    'obsolescence_score': row.get('obsolescence_score', None),
                    'confidence': row.get('confidence', None),
                    'tile_count': row.get('tile_count', None)
                }
    
    # Add region information to counties
    counties_gdf['REGION'] = counties_gdf['STATEFP'].apply(get_region)
    
    # Generate scores for all counties
    print("Generating comprehensive county data...")
    for idx, row in counties_gdf.iterrows():
        geoid = row['GEOID']
        
        # If we have existing data for this county, use it
        if geoid in existing_data:
            counties_gdf.at[idx, 'obsolescence_score'] = existing_data[geoid]['obsolescence_score']
            counties_gdf.at[idx, 'confidence'] = existing_data[geoid]['confidence']
            counties_gdf.at[idx, 'tile_count'] = existing_data[geoid]['tile_count']
        else:
            # Generate new data
            if regional:
                # Generate score based on region
                score = generate_regional_score(row['REGION'])
            else:
                # Generate random score
                score = np.random.random()
            
            counties_gdf.at[idx, 'obsolescence_score'] = score
            counties_gdf.at[idx, 'confidence'] = 0.5 + np.random.random() * 0.5  # Between 0.5 and 1.0
            counties_gdf.at[idx, 'tile_count'] = int(5 + np.random.random() * 20)  # Between 5 and 25
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save the comprehensive county data
    counties_gdf.to_file(output_file, driver='GeoJSON')
    print(f"Saved comprehensive county data to {output_file}")
    
    # Print some statistics
    print(f"\nGenerated data for {len(counties_gdf)} counties")
    print(f"Existing data preserved for {len(existing_data)} counties")
    print(f"New data generated for {len(counties_gdf) - len(existing_data)} counties")
    
    if regional:
        # Print regional statistics
        print("\nRegional Statistics:")
        for region in ['Northeast', 'Midwest', 'South', 'West']:
            region_data = counties_gdf[counties_gdf['REGION'] == region]
            mean_score = region_data['obsolescence_score'].mean()
            print(f"{region}: {len(region_data)} counties, Mean Score: {mean_score:.2f}")

def main():
    """Main function."""
    args = parse_args()
    generate_comprehensive_county_data(
        args.input, args.shapefile, args.output, args.regional, args.seed
    )

if __name__ == "__main__":
    main()
