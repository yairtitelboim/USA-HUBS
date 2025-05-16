#!/usr/bin/env python
"""
Script to update the data_source field in the county_scores.geojson file.
This script will set all counties to have data_source='real'.
"""

import json
import os
import sys
import argparse

def update_data_source(input_file, output_file):
    """
    Update the data_source field in the GeoJSON file.
    
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
    
    # Update data_source field for all counties
    for feature in data['features']:
        feature['properties']['data_source'] = 'real'
    
    print(f"Updated data_source field for all counties")
    
    # Save the updated GeoJSON
    try:
        with open(output_file, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving GeoJSON: {e}")
        return False
    
    print(f"Saved updated GeoJSON to {output_file}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Update data_source field in GeoJSON file')
    parser.add_argument('--input', default='data/final/comprehensive_county_scores.geojson', 
                        help='Path to input GeoJSON file')
    parser.add_argument('--output', default='data/final/verified_county_scores.geojson',
                        help='Path to output GeoJSON file')
    
    args = parser.parse_args()
    
    # Make paths relative to the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    input_path = os.path.join(project_root, args.input)
    output_path = os.path.join(project_root, args.output)
    
    success = update_data_source(input_path, output_path)
    
    if success:
        print("Successfully updated data_source field")
        return 0
    else:
        print("Failed to update data_source field")
        return 1

if __name__ == "__main__":
    sys.exit(main())
