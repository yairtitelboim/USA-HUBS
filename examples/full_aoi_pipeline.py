#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Production-scale satellite imagery pipeline for the full AOI.

This script implements Phase 1 of the production pipeline:
1. Generate & review full AOI tile grid
2. Configure & kick off batch exports
3. Monitor & retry failures
4. Build & audit the manifest
5. Ingest & benchmark with PyTorch Dataset
6. Visual sanity check
"""

import os
import sys
import subprocess
import json
import argparse
import time
from datetime import datetime

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Constants
DEFAULT_BUCKET = "loghub-sentinel2-exports"
DEFAULT_PROJECT = "gentle-cinema-458613-f3"
DEFAULT_TILE_SIZE = 256
DEFAULT_RESOLUTION = 10
DEFAULT_CHUNK_SIZE = 500
DEFAULT_SAMPLE_SIZE = 100

def run_command(command, check=True):
    """
    Run a command and print the output.

    Args:
        command: Command to run
        check: Whether to check for errors

    Returns:
        Command output
    """
    print(f"Running command: {command}")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"Error output: {e.stderr}")
        if check:
            raise
        return e.stderr

def generate_tile_grid(aoi_path, tile_size, resolution, output_name):
    """
    Generate a tile grid for the AOI.

    Args:
        aoi_path: Path to the AOI GeoJSON file
        tile_size: Tile size in pixels
        resolution: Resolution in meters per pixel
        output_name: Output file name

    Returns:
        Path to the generated tile grid
    """
    print(f"Generating tile grid for {aoi_path}...")

    command = (
        f"python ../create_tile_grid.py "
        f"--aoi-file {aoi_path} "
        f"--tile-size {tile_size} "
        f"--resolution {resolution} "
        f"--output-name {output_name}"
    )

    # Fix path if running from examples directory
    if not os.path.exists("../create_tile_grid.py"):
        command = command.replace("../create_tile_grid.py", "../LOGhub/create_tile_grid.py")
        if not os.path.exists("../LOGhub/create_tile_grid.py"):
            command = command.replace("../LOGhub/create_tile_grid.py", "create_tile_grid.py")

    run_command(command)

    # Return the path to the generated tile grid
    return f"../tiles/{output_name}"

def configure_batch_exports(tiles_path, start_date, end_date, bucket, project, chunk_size, region_prefix=None):
    """
    Configure and kick off batch exports.

    Args:
        tiles_path: Path to the tile grid JSON file
        start_date: Start date in format YYYY-MM-DD
        end_date: End date in format YYYY-MM-DD
        bucket: Google Cloud Storage bucket name
        project: Google Cloud project ID
        chunk_size: Number of tasks to submit in each batch
        region_prefix: Optional prefix for the region (e.g., 'south', 'west', 'east')

    Returns:
        None
    """
    print(f"Configuring batch exports for {tiles_path}...")

    # Check if the bucket exists and create it if it doesn't
    bucket_check_command = f"gsutil ls -b gs://{bucket} || gsutil mb gs://{bucket}"
    try:
        run_command(bucket_check_command, check=False)
    except subprocess.CalledProcessError:
        print(f"Creating bucket gs://{bucket}...")
        run_command(f"gsutil mb gs://{bucket}")

    # Grant the service account write access to the bucket
    service_account = f"loghub-ee-sa@{project}.iam.gserviceaccount.com"
    grant_access_command = (
        f"gsutil iam ch "
        f"serviceAccount:{service_account}:objectAdmin "
        f"gs://{bucket}"
    )
    run_command(grant_access_command, check=False)

    # Submit batch exports
    export_command = (
        f"python ../batch_export_sentinel2.py "
        f"{tiles_path} {start_date} {end_date} "
        f"--bucket {bucket} --project {project} "
        f"--batch-size {chunk_size}"
    )

    # Add region prefix if specified
    if region_prefix:
        export_command += f" --region-prefix {region_prefix}"

    run_command(export_command)

    # Verify tasks registered
    list_command = f"python ../monitor_ee_tasks.py --project {project} --report ../qa/tasks_initial.json"
    run_command(list_command)

def monitor_and_retry(project, retry_failed=True, cancel_stalled=True):
    """
    Monitor and retry failed tasks.

    Args:
        project: Google Cloud project ID
        retry_failed: Whether to retry failed tasks
        cancel_stalled: Whether to cancel stalled tasks

    Returns:
        None
    """
    print("Monitoring and retrying tasks...")

    # Create timestamp for report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Build command
    command = f"python ../monitor_ee_tasks.py --project {project}"

    if retry_failed:
        command += " --status FAILED --retry"

    if cancel_stalled:
        command += " --status RUNNING --cancel"

    command += f" --report ../qa/tasks_{timestamp}.json"

    run_command(command)

def build_and_audit_manifest(bucket, start_date, end_date, output_name, sample_size, region_prefix=None):
    """
    Build and audit the manifest.

    Args:
        bucket: Google Cloud Storage bucket name
        start_date: Start date in format YYYY-MM-DD
        end_date: End date in format YYYY-MM-DD
        output_name: Output file name
        sample_size: Number of samples to download
        region_prefix: Optional prefix for the region (e.g., 'south', 'west', 'east')

    Returns:
        Path to the generated manifest
    """
    print("Building and auditing manifest...")

    # Create timestamp for file names
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Generate manifest
    manifest_path = f"../manifests/{output_name}"

    # Extract year from start date
    start_year = start_date.split("-")[0]

    # Set prefix based on region or year
    if region_prefix:
        prefix = f"{region_prefix}"
    else:
        prefix = f"{start_year}-"

    manifest_command = (
        f"python ../create_manifest.py {bucket} "
        f"--prefix {prefix} "
        f"--start-date {start_date} "
        f"--end-date {end_date} "
        f"--manifest {manifest_path}"
    )

    run_command(manifest_command)

    # Download a QC sample
    sample_command = (
        f"python ../create_manifest.py {bucket} "
        f"--prefix {prefix} "
        f"--start-date {start_date} "
        f"--end-date {end_date} "
        f"--manifest {manifest_path} "
        f"--download --sample-size {sample_size} "
        f"--analyze --report ../qa/sample_analysis_{timestamp}.json "
        f"--mosaic --mosaic-output ../qa/mosaic_{timestamp}.png"
    )

    run_command(sample_command)

    return manifest_path

def benchmark_dataset(manifest_path, data_dir, sample_size):
    """
    Benchmark the PyTorch Dataset.

    Args:
        manifest_path: Path to the manifest file
        data_dir: Directory containing the downloaded samples
        sample_size: Number of samples to benchmark

    Returns:
        None
    """
    print("Benchmarking PyTorch Dataset...")

    command = (
        f"python ../test_data_loader.py "
        f"--manifest {manifest_path} "
        f"--data-dir {data_dir} "
        f"--sample-size {sample_size}"
    )

    run_command(command)

def main():
    """Main function to run the full AOI pipeline."""
    parser = argparse.ArgumentParser(description="Production-scale satellite imagery pipeline")

    # AOI options
    parser.add_argument("--aoi", required=True, help="Path to the AOI GeoJSON file")

    # Date range options
    parser.add_argument("--start-date", default="2023-11-01", help="Start date in format YYYY-MM-DD")
    parser.add_argument("--end-date", default="2025-05-01", help="End date in format YYYY-MM-DD")

    # Tile grid options
    parser.add_argument("--tile-size", type=int, default=DEFAULT_TILE_SIZE,
                        help=f"Tile size in pixels (default: {DEFAULT_TILE_SIZE})")
    parser.add_argument("--resolution", type=float, default=DEFAULT_RESOLUTION,
                        help=f"Resolution in meters per pixel (default: {DEFAULT_RESOLUTION})")

    # Export options
    parser.add_argument("--bucket", default=DEFAULT_BUCKET,
                        help=f"Google Cloud Storage bucket name (default: {DEFAULT_BUCKET})")
    parser.add_argument("--project", default=DEFAULT_PROJECT,
                        help=f"Google Cloud project ID (default: {DEFAULT_PROJECT})")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE,
                        help=f"Number of tasks to submit in each batch (default: {DEFAULT_CHUNK_SIZE})")
    parser.add_argument("--region-prefix", default=None,
                        help="Region prefix for file names (e.g., 'south', 'west', 'east')")

    # Manifest options
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE,
                        help=f"Number of samples to download (default: {DEFAULT_SAMPLE_SIZE})")

    # Pipeline control options
    parser.add_argument("--skip-grid", action="store_true", help="Skip tile grid generation")
    parser.add_argument("--skip-export", action="store_true", help="Skip batch export")
    parser.add_argument("--skip-monitor", action="store_true", help="Skip monitoring and retrying")
    parser.add_argument("--skip-manifest", action="store_true", help="Skip manifest building and auditing")
    parser.add_argument("--skip-benchmark", action="store_true", help="Skip dataset benchmarking")

    args = parser.parse_args()

    # Create timestamp for file names
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Step 1: Generate & review full AOI tile grid
    tile_grid_path = None
    if not args.skip_grid:
        output_name = f"tiles_full_{timestamp}.json"
        tile_grid_path = generate_tile_grid(args.aoi, args.tile_size, args.resolution, output_name)
        print(f"Tile grid generated: {tile_grid_path}")
        print("Please review the tile grid in QGIS or geojson.io before proceeding.")

        # Pause for user review
        input("Press Enter to continue...")
    else:
        # Use the most recent tile grid
        tile_grid_files = sorted(os.listdir("../tiles"))
        if tile_grid_files:
            tile_grid_path = f"../tiles/{tile_grid_files[-1]}"
            print(f"Using existing tile grid: {tile_grid_path}")
        else:
            print("No existing tile grid found. Please run without --skip-grid.")
            return

    # Step 2: Configure & kick off batch exports
    if not args.skip_export:
        configure_batch_exports(
            tile_grid_path, args.start_date, args.end_date,
            args.bucket, args.project, args.chunk_size,
            args.region_prefix
        )

    # Step 3: Monitor & retry failures
    if not args.skip_monitor:
        monitor_and_retry(args.project)

    # Step 4: Build & audit the manifest
    manifest_path = None
    if not args.skip_manifest:
        output_name = f"manifest_full_{timestamp}.txt"
        manifest_path = build_and_audit_manifest(
            args.bucket, args.start_date, args.end_date,
            output_name, args.sample_size, args.region_prefix
        )
        print(f"Manifest generated: {manifest_path}")
    else:
        # Use the most recent manifest
        manifest_files = sorted(os.listdir("../manifests"))
        if manifest_files:
            manifest_path = f"../manifests/{manifest_files[-1]}"
            print(f"Using existing manifest: {manifest_path}")
        else:
            print("No existing manifest found. Please run without --skip-manifest.")
            return

    # Step 5: Ingest & benchmark with PyTorch Dataset
    if not args.skip_benchmark:
        benchmark_dataset(manifest_path, "../data/raw", args.sample_size)

    print("Full AOI pipeline completed successfully!")

if __name__ == "__main__":
    main()
