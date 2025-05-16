#!/usr/bin/env python3
"""
Process Multiple Counties with Real Satellite Data

This script processes multiple counties with real satellite data using the
process_real_satellite_only.py script. It takes a list of county FIPS codes
and processes them one by one.

Usage:
    python process_multiple_counties.py --counties FIPS1,FIPS2,FIPS3 --output OUTPUT_FILE

Options:
    --counties COUNTIES  Comma-separated list of county FIPS codes to process
    --output OUTPUT_FILE Path to save the updated county scores [default: data/final/county_scores.geojson]
    --service-account-key PATH  Path to Google Earth Engine service account key
"""

import os
import argparse
import subprocess
import time
import sys

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process Multiple Counties with Real Satellite Data')
    parser.add_argument('--counties', required=True,
                        help='Comma-separated list of county FIPS codes to process')
    parser.add_argument('--output', default='data/final/county_scores.geojson',
                        help='Path to save the updated county scores')
    parser.add_argument('--service-account-key',
                        default='config/gee/gentle-cinema-458613-f3-51d8ea2711e7.json',
                        help='Path to Google Earth Engine service account key')
    return parser.parse_args()

def process_county(county_fips, output_file, service_account_key):
    """
    Process a single county with real satellite data.

    Args:
        county_fips: FIPS code of the county to process
        output_file: Path to save the updated county scores
        service_account_key: Path to Google Earth Engine service account key

    Returns:
        True if processing was successful, False otherwise
    """
    print(f"Processing county {county_fips}...")
    
    # Build the command
    command = [
        "python", "tools/process_real_satellite_only.py",
        "--county", county_fips,
        "--output", output_file
    ]
    
    if service_account_key:
        command.extend(["--service-account-key", service_account_key])
    
    # Run the command
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error processing county {county_fips}: {e}")
        print(f"Error output: {e.stderr}")
        return False

def process_counties(county_list, output_file, service_account_key):
    """
    Process multiple counties with real satellite data.

    Args:
        county_list: List of county FIPS codes to process
        output_file: Path to save the updated county scores
        service_account_key: Path to Google Earth Engine service account key

    Returns:
        Number of successfully processed counties
    """
    print(f"Processing {len(county_list)} counties with real satellite data...")
    
    # Process each county
    success_count = 0
    for i, county_fips in enumerate(county_list):
        print(f"Processing county {i+1}/{len(county_list)}: {county_fips}")
        
        # Process the county
        success = process_county(county_fips, output_file, service_account_key)
        
        # Update success count
        if success:
            success_count += 1
            print(f"Successfully processed county {county_fips}")
        else:
            print(f"Failed to process county {county_fips}")
        
        # Add a small delay between counties to avoid rate limiting
        if i < len(county_list) - 1:
            print("Waiting 5 seconds before processing the next county...")
            time.sleep(5)
    
    return success_count

def main():
    """Main function."""
    args = parse_args()
    
    # Parse the county list
    county_list = args.counties.split(',')
    
    # Process the counties
    success_count = process_counties(county_list, args.output, args.service_account_key)
    
    # Print summary
    print(f"Successfully processed {success_count}/{len(county_list)} counties")
    
    # Copy the file to the React app's public directory
    react_app_dir = "county-viz-app/public/data/final/"
    os.makedirs(react_app_dir, exist_ok=True)
    try:
        subprocess.run(["cp", args.output, react_app_dir], check=True)
        print(f"Copied {args.output} to {react_app_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Error copying file to React app directory: {e}")
    
    return 0 if success_count == len(county_list) else 1

if __name__ == "__main__":
    sys.exit(main())
