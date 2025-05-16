#!/usr/bin/env python3
"""
Fix the county_scores.geojson file by ensuring it's valid JSON.
"""

import json
import os
import sys
import geopandas as gpd
from pathlib import Path

def fix_county_scores(input_file, output_file=None):
    """
    Fix the county_scores.geojson file by reading it with geopandas and writing it back out.
    
    Args:
        input_file (str): Path to the input GeoJSON file
        output_file (str, optional): Path to the output GeoJSON file. If None, overwrites the input file.
    """
    print(f"Attempting to fix {input_file}...")
    
    try:
        # Try to read the file with geopandas
        gdf = gpd.read_file(input_file)
        print(f"Successfully read {len(gdf)} counties from {input_file}")
        
        # Write the file back out
        if output_file is None:
            output_file = input_file
            
        # Create a backup of the original file
        backup_file = f"{input_file}.bak"
        if not os.path.exists(backup_file):
            print(f"Creating backup at {backup_file}")
            os.system(f"cp {input_file} {backup_file}")
        
        # Write the fixed file
        print(f"Writing fixed file to {output_file}")
        gdf.to_file(output_file, driver="GeoJSON")
        print(f"Successfully wrote {len(gdf)} counties to {output_file}")
        
        return True
    except Exception as e:
        print(f"Error fixing {input_file}: {e}")
        return False

def main():
    """Main function."""
    # Get the path to the county_scores.geojson file
    repo_root = Path(__file__).parent.parent
    county_scores_path = repo_root / "data" / "final" / "county_scores.geojson"
    
    # Fix the file
    success = fix_county_scores(county_scores_path)
    
    # Also fix the copy in the React app's public directory
    react_county_scores_path = repo_root / "county-viz-app" / "public" / "data" / "final" / "county_scores.geojson"
    if os.path.exists(react_county_scores_path):
        print(f"\nFixing React app copy at {react_county_scores_path}")
        if success:
            # If we successfully fixed the original, just copy it
            os.system(f"cp {county_scores_path} {react_county_scores_path}")
            print(f"Copied fixed file to {react_county_scores_path}")
        else:
            # Otherwise, try to fix the React app copy directly
            fix_county_scores(react_county_scores_path)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
