#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example script for processing Sentinel-2 imagery for Houston.

This script demonstrates how to use the LOGhub pipeline to process Sentinel-2 imagery
for a small area in Houston, TX.
"""

import os
import sys
import subprocess
import json
from datetime import datetime

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define the Houston AOI (bounding box)
HOUSTON_AOI = [-95.37, 29.74, -95.36, 29.75]

# Define the date range
START_DATE = "2024-01"
END_DATE = "2024-03"

# Define the Google Cloud Storage bucket
BUCKET = "loghub-sentinel2-exports"

# Define the Google Cloud project ID
PROJECT = "gentle-cinema-458613-f3"

def run_command(command):
    """
    Run a command and print the output.
    
    Args:
        command: Command to run
        
    Returns:
        Command output
    """
    print(f"Running command: {command}")
    result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
    print(result.stdout)
    return result.stdout

def main():
    """Main function to run the Houston example."""
    # Create timestamp for file names
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Step 1: Create a tile grid
    print("Step 1: Creating tile grid...")
    tile_grid_command = (
        f"python ../create_tile_grid.py "
        f"--bbox {HOUSTON_AOI[0]} {HOUSTON_AOI[1]} {HOUSTON_AOI[2]} {HOUSTON_AOI[3]} "
        f"--tile-size 256 --resolution 10 "
        f"--output-name houston_{timestamp}.json"
    )
    run_command(tile_grid_command)
    
    # Get the path to the tile grid file
    tile_grid_path = f"../tiles/houston_{timestamp}.json"
    
    # Step 2: Check if the bucket exists and create it if it doesn't
    print("Step 2: Checking if the bucket exists...")
    bucket_check_command = f"gsutil ls -b gs://{BUCKET} || gsutil mb gs://{BUCKET}"
    try:
        run_command(bucket_check_command)
    except subprocess.CalledProcessError:
        print(f"Creating bucket gs://{BUCKET}...")
        run_command(f"gsutil mb gs://{BUCKET}")
    
    # Step 3: Grant the service account write access to the bucket
    print("Step 3: Granting service account write access to the bucket...")
    service_account = f"loghub-ee-sa@{PROJECT}.iam.gserviceaccount.com"
    grant_access_command = (
        f"gsutil iam ch "
        f"serviceAccount:{service_account}:objectAdmin "
        f"gs://{BUCKET}"
    )
    run_command(grant_access_command)
    
    # Step 4: Batch export Sentinel-2 imagery
    print("Step 4: Batch exporting Sentinel-2 imagery...")
    export_command = (
        f"python ../batch_export_sentinel2.py "
        f"{tile_grid_path} {START_DATE} {END_DATE} "
        f"--bucket {BUCKET} --project {PROJECT} "
        f"--batch-size 10 --monitor"
    )
    run_command(export_command)
    
    # Step 5: Create a manifest and download samples
    print("Step 5: Creating manifest and downloading samples...")
    manifest_command = (
        f"python ../create_manifest.py {BUCKET} "
        f"--prefix {START_DATE.split('-')[0]}- "
        f"--manifest ../manifests/houston_{timestamp}.txt "
        f"--download --sample-size 5 --analyze --mosaic"
    )
    run_command(manifest_command)
    
    # Step 6: Test the data loader
    print("Step 6: Testing the data loader...")
    test_command = (
        f"python ../test_data_loader.py "
        f"--manifest ../manifests/houston_{timestamp}.txt "
        f"--data-dir ../data/raw "
        f"--sample-size 5 "
        f"--output-dir ../qa/houston_{timestamp}"
    )
    run_command(test_command)
    
    print("Houston example completed successfully!")

if __name__ == "__main__":
    # Create the examples directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    
    main()
