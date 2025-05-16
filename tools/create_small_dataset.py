#!/usr/bin/env python
"""
Script to create a small version of the county_scores.geojson file for testing.
"""

import json
import os
import sys
import argparse

def create_small_dataset(input_file, output_file, num_counties=100):
    """
    Create a small version of the GeoJSON file.
    
    Args:
        input_file (str): Path to the input GeoJSON file
        output_file (str): Path to the output GeoJSON file
        num_counties (int): Number of counties to include in the small dataset
    """
    print(f"Loading GeoJSON from {input_file}")
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading GeoJSON: {e}")
        return False
    
    print(f"Loaded {len(data['features'])} counties")
    
    # Create small dataset
    small_data = {
        'type': 'FeatureCollection',
        'features': data['features'][:num_counties]
    }
    
    print(f"Created small dataset with {len(small_data['features'])} counties")
    
    # Save the small dataset
    try:
        with open(output_file, 'w') as f:
            json.dump(small_data, f)
    except Exception as e:
        print(f"Error saving GeoJSON: {e}")
        return False
    
    print(f"Saved small dataset to {output_file}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Create small dataset from GeoJSON file')
    parser.add_argument('--input', default='data/final/verified_county_scores.geojson', 
                        help='Path to input GeoJSON file')
    parser.add_argument('--output', default='data/final/verified_county_scores_small.geojson',
                        help='Path to output GeoJSON file')
    parser.add_argument('--num-counties', type=int, default=100,
                        help='Number of counties to include in the small dataset')
    
    args = parser.parse_args()
    
    # Make paths relative to the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    input_path = os.path.join(project_root, args.input)
    output_path = os.path.join(project_root, args.output)
    
    success = create_small_dataset(input_path, output_path, args.num_counties)
    
    if success:
        print("Successfully created small dataset")
        return 0
    else:
        print("Failed to create small dataset")
        return 1

if __name__ == "__main__":
    sys.exit(main())
