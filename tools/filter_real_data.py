#!/usr/bin/env python
"""
Script to filter the county_scores.geojson file to only include counties with real data.
"""

import json
import os
import sys
import argparse

def filter_real_data(input_file, output_file):
    """
    Filter the GeoJSON file to only include counties with real data.
    
    Args:
        input_file (str): Path to the input GeoJSON file
        output_file (str): Path to the output GeoJSON file
    """
    print(f"Loading GeoJSON from {input_file}")
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading GeoJSON: {e}")
        return False
    
    print(f"Loaded {len(data['features'])} counties")
    
    # Filter for real data
    real_data = [f for f in data['features'] if f['properties'].get('data_source') == 'real']
    
    print(f"Found {len(real_data)} counties with real data ({len(real_data)/len(data['features']):.1%})")
    
    # Create filtered dataset
    filtered_data = {
        'type': 'FeatureCollection',
        'features': real_data
    }
    
    # Save the filtered dataset
    try:
        with open(output_file, 'w') as f:
            json.dump(filtered_data, f)
    except Exception as e:
        print(f"Error saving GeoJSON: {e}")
        return False
    
    print(f"Saved filtered dataset to {output_file}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Filter GeoJSON file to only include counties with real data')
    parser.add_argument('--input', default='data/final/county_scores_with_source.geojson', 
                        help='Path to input GeoJSON file')
    parser.add_argument('--output', default='data/final/verified_county_scores.geojson',
                        help='Path to output GeoJSON file')
    
    args = parser.parse_args()
    
    # Make paths relative to the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    input_path = os.path.join(project_root, args.input)
    output_path = os.path.join(project_root, args.output)
    
    success = filter_real_data(input_path, output_path)
    
    if success:
        print("Successfully filtered for real data")
        return 0
    else:
        print("Failed to filter for real data")
        return 1

if __name__ == "__main__":
    sys.exit(main())
