#!/usr/bin/env python3
"""
Filter Real County Data

This script filters the county_scores.geojson file to include only counties with real data
and adds a data_source field to distinguish between real and simulated data.

Usage:
    python filter_real_county_data.py [--input INPUT_FILE] [--output OUTPUT_FILE] [--comprehensive COMPREHENSIVE_FILE]

Options:
    --input INPUT_FILE            Path to the real county scores GeoJSON [default: data/final/county_scores.geojson]
    --output OUTPUT_FILE          Path to save the filtered real county scores [default: data/final/county_scores_real.geojson]
    --comprehensive COMPREHENSIVE_FILE  Path to save the comprehensive data with data_source field [default: data/final/county_scores_with_source.geojson]
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
    parser = argparse.ArgumentParser(description='Filter real county data')
    parser.add_argument('--input', default='data/final/county_scores.geojson',
                        help='Path to the real county scores GeoJSON')
    parser.add_argument('--output', default='data/final/county_scores_real.geojson',
                        help='Path to save the filtered real county scores')
    parser.add_argument('--comprehensive', default='data/final/county_scores_with_source.geojson',
                        help='Path to save the comprehensive data with data_source field')
    return parser.parse_args()

def filter_real_county_data(input_file, output_file, comprehensive_file):
    """Filter the county_scores.geojson file to include only counties with real data."""
    print(f"Loading county data from {input_file}...")
    
    # Load the GeoJSON file with real data
    try:
        real_gdf = gpd.read_file(input_file)
        print(f"Loaded {len(real_gdf)} counties from real data GeoJSON file")
    except Exception as e:
        print(f"Error loading real data GeoJSON file: {e}")
        return
    
    # Add data_source field to real data
    real_gdf['data_source'] = 'real'
    
    # Save the filtered real county data
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    real_gdf.to_file(output_file, driver='GeoJSON')
    print(f"Saved {len(real_gdf)} counties with real data to {output_file}")
    
    # Load the comprehensive county data if it exists
    comprehensive_path = 'data/final/comprehensive_county_scores.geojson'
    if os.path.exists(comprehensive_path):
        try:
            print(f"Loading comprehensive county data from {comprehensive_path}...")
            comp_gdf = gpd.read_file(comprehensive_path)
            print(f"Loaded {len(comp_gdf)} counties from comprehensive GeoJSON file")
            
            # Create a set of GEOIDs from real data for quick lookup
            real_geoids = set(real_gdf['GEOID'].values)
            
            # Add data_source field to comprehensive data
            comp_gdf['data_source'] = comp_gdf['GEOID'].apply(
                lambda x: 'real' if x in real_geoids else 'simulated')
            
            # Count real vs simulated
            real_count = len(comp_gdf[comp_gdf['data_source'] == 'real'])
            simulated_count = len(comp_gdf[comp_gdf['data_source'] == 'simulated'])
            print(f"Comprehensive data contains {real_count} real counties and {simulated_count} simulated counties")
            
            # Save the comprehensive data with data_source field
            os.makedirs(os.path.dirname(comprehensive_file), exist_ok=True)
            comp_gdf.to_file(comprehensive_file, driver='GeoJSON')
            print(f"Saved comprehensive data with data_source field to {comprehensive_file}")
            
        except Exception as e:
            print(f"Error processing comprehensive data: {e}")
    else:
        print(f"Comprehensive county data file not found: {comprehensive_path}")

def main():
    """Main function."""
    args = parse_args()
    filter_real_county_data(args.input, args.output, args.comprehensive)

if __name__ == "__main__":
    main()
