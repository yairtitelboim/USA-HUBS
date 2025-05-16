#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Batch export Sentinel-2 imagery for a grid of tiles.

This script exports Sentinel-2 imagery for each tile in a grid,
for each month in a specified date range, to Google Cloud Storage.
"""

import os
import json
import argparse
import time
from datetime import datetime, timedelta
import ee

# Constants
DEFAULT_BUCKET = "loghub-sentinel2-exports"
DEFAULT_BANDS = ["B4", "B3", "B2"]
DEFAULT_SCALE = 10
DEFAULT_CRS = "EPSG:3857"
DEFAULT_MAX_PIXELS = 1e10
DEFAULT_BATCH_SIZE = 500
DEFAULT_BATCH_PAUSE = 120  # seconds

def parse_date(date_str):
    """
    Parse a date string into a datetime object.

    Args:
        date_str: Date string in format 'YYYY-MM' or 'YYYY-MM-DD'

    Returns:
        Datetime object
    """
    if len(date_str.split('-')) == 2:
        # Format: YYYY-MM
        return datetime.strptime(date_str, '%Y-%m')
    else:
        # Format: YYYY-MM-DD
        return datetime.strptime(date_str, '%Y-%m-%d')

def next_month(date_str):
    """
    Get the first day of the next month after the given date.

    Args:
        date_str: Date string in format 'YYYY-MM' or 'YYYY-MM-DD'

    Returns:
        String representing the first day of the next month in format 'YYYY-MM-DD'
    """
    # Parse the date
    date = parse_date(date_str)

    # Get the first day of the next month
    if date.month == 12:
        next_year = date.year + 1
        next_month = 1
    else:
        next_year = date.year
        next_month = date.month + 1

    return f"{next_year}-{next_month:02d}-01"

def mask_s2_clouds(img):
    """
    Mask clouds in Sentinel-2 imagery.

    Args:
        img: Earth Engine image

    Returns:
        Earth Engine image with clouds masked
    """
    # Use the cloud probability band (MSK_CLDPRB) and cloud classification bands
    cloudProb = img.select('MSK_CLDPRB')
    cloudOpaque = img.select('MSK_CLASSI_OPAQUE')
    cloudCirrus = img.select('MSK_CLASSI_CIRRUS')

    # Create a combined mask (cloud probability < 50% AND not classified as opaque or cirrus cloud)
    mask = cloudProb.lt(50).And(cloudOpaque.eq(0)).And(cloudCirrus.eq(0))

    # Apply the mask and scale the pixel values
    return img.updateMask(mask).divide(10000)

def export_tile(tile, date_str, bucket, bands=DEFAULT_BANDS, scale=DEFAULT_SCALE,
               crs=DEFAULT_CRS, max_pixels=DEFAULT_MAX_PIXELS, region_prefix=None):
    """
    Export Sentinel-2 imagery for a tile and date.

    Args:
        tile: Dictionary containing tile ID and geometry
        date_str: Date string in format 'YYYY-MM'
        bucket: Google Cloud Storage bucket name
        bands: List of bands to export
        scale: Resolution in meters per pixel
        crs: Coordinate reference system
        max_pixels: Maximum number of pixels to export
        region_prefix: Optional prefix for the region (e.g., 'south', 'west', 'east')

    Returns:
        Earth Engine task
    """
    # Convert tile geometry to Earth Engine geometry
    ee_geometry = ee.Geometry(tile["geom"])

    # Get the next month
    next_month_str = next_month(date_str)

    # Create a median composite for the month
    image = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
             .filterBounds(ee_geometry)
             .filterDate(date_str, next_month_str)
             .map(mask_s2_clouds)
             .median()
             .select(bands))

    # Create a description for the task
    if region_prefix:
        description = f"{region_prefix}_{date_str}_{tile['id']}"
    else:
        description = f"{date_str}_{tile['id']}"

    # Create a file name prefix
    if region_prefix:
        file_name_prefix = f"{region_prefix}/{date_str}/{tile['id']}"
    else:
        file_name_prefix = f"{date_str}/{tile['id']}"

    # Create and start the export task
    task = ee.batch.Export.image.toCloudStorage(
        image=image,
        description=description,
        bucket=bucket,
        fileNamePrefix=file_name_prefix,
        region=ee_geometry,
        scale=scale,
        crs=crs,
        maxPixels=max_pixels,
        fileFormat="GeoTIFF",
        formatOptions={"cloudOptimized": True}
    )

    task.start()

    return task

def load_tiles(tiles_path):
    """
    Load tiles from a JSON file.

    Args:
        tiles_path: Path to the tiles JSON file

    Returns:
        List of tiles
    """
    with open(tiles_path, 'r') as f:
        return json.load(f)

def generate_date_range(start_date, end_date):
    """
    Generate a list of month strings between start_date and end_date.

    Args:
        start_date: Start date string in format 'YYYY-MM' or 'YYYY-MM-DD'
        end_date: End date string in format 'YYYY-MM' or 'YYYY-MM-DD'

    Returns:
        List of month strings in format 'YYYY-MM'
    """
    # Parse the dates
    start = parse_date(start_date)
    end = parse_date(end_date)

    date_list = []
    year = start.year
    month = start.month

    while (year < end.year) or (year == end.year and month <= end.month):
        date_list.append(f"{year}-{month:02d}")

        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return date_list

def monitor_tasks(tasks, interval=60, max_checks=100):
    """
    Monitor the status of Earth Engine tasks.

    Args:
        tasks: List of Earth Engine tasks
        interval: Interval in seconds between status checks
        max_checks: Maximum number of status checks

    Returns:
        Dictionary with task status counts
    """
    all_complete = False
    check_count = 0

    while not all_complete and check_count < max_checks:
        statuses = {}
        all_complete = True

        for task in tasks:
            status = task.status()['state']
            statuses[status] = statuses.get(status, 0) + 1

            if status not in ['COMPLETED', 'FAILED', 'CANCELLED']:
                all_complete = False

        print(f"Task status: {statuses}")

        if not all_complete:
            print(f"Waiting {interval} seconds for tasks to complete...")
            time.sleep(interval)
            check_count += 1

    return statuses

def main():
    """Main function to batch export Sentinel-2 imagery."""
    parser = argparse.ArgumentParser(description="Batch export Sentinel-2 imagery")

    # Required arguments
    parser.add_argument("tiles_path", help="Path to tiles JSON file")
    parser.add_argument("start_date", help="Start date in format YYYY-MM")
    parser.add_argument("end_date", help="End date in format YYYY-MM")

    # Optional arguments
    parser.add_argument("--bucket", default=DEFAULT_BUCKET,
                        help=f"Google Cloud Storage bucket name (default: {DEFAULT_BUCKET})")
    parser.add_argument("--bands", nargs='+', default=DEFAULT_BANDS,
                        help=f"Bands to export (default: {DEFAULT_BANDS})")
    parser.add_argument("--scale", type=float, default=DEFAULT_SCALE,
                        help=f"Resolution in meters per pixel (default: {DEFAULT_SCALE})")
    parser.add_argument("--crs", default=DEFAULT_CRS,
                        help=f"Coordinate reference system (default: {DEFAULT_CRS})")
    parser.add_argument("--max-pixels", type=float, default=DEFAULT_MAX_PIXELS,
                        help=f"Maximum number of pixels to export (default: {DEFAULT_MAX_PIXELS})")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help=f"Number of tasks to submit in each batch (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--batch-pause", type=int, default=DEFAULT_BATCH_PAUSE,
                        help=f"Pause between batches in seconds (default: {DEFAULT_BATCH_PAUSE})")
    parser.add_argument("--project", default=None,
                        help="Google Cloud project ID (default: None)")
    parser.add_argument("--region-prefix", default=None,
                        help="Region prefix for file names (e.g., 'south', 'west', 'east')")
    parser.add_argument("--monitor", action="store_true",
                        help="Monitor task status after submission")

    args = parser.parse_args()

    # Initialize Earth Engine
    try:
        ee.Initialize(project=args.project)
        print("Earth Engine initialized successfully!")
    except Exception as e:
        print(f"Error initializing Earth Engine: {e}")
        return

    # Load tiles
    tiles = load_tiles(args.tiles_path)
    print(f"Loaded {len(tiles)} tiles from {args.tiles_path}")

    # Generate date range
    dates = generate_date_range(args.start_date, args.end_date)
    print(f"Generated {len(dates)} months from {args.start_date} to {args.end_date}")

    # Export tiles for each date
    all_tasks = []
    task_count = 0
    batch_count = 0

    for date in dates:
        print(f"Processing date: {date}")

        for i, tile in enumerate(tiles):
            # Export tile
            task = export_tile(
                tile=tile,
                date_str=date,
                bucket=args.bucket,
                bands=args.bands,
                scale=args.scale,
                crs=args.crs,
                max_pixels=args.max_pixels,
                region_prefix=args.region_prefix
            )

            all_tasks.append(task)
            task_count += 1

            # Print progress
            if (i + 1) % 10 == 0:
                print(f"  Submitted {i + 1}/{len(tiles)} tiles for {date}")

            # Check if we need to pause between batches
            if task_count % args.batch_size == 0:
                batch_count += 1
                print(f"Submitted batch {batch_count} ({args.batch_size} tasks)")
                print(f"Pausing for {args.batch_pause} seconds to avoid quota limits...")
                time.sleep(args.batch_pause)

    print(f"Submitted {task_count} tasks in {batch_count + 1} batches")

    # Monitor tasks if requested
    if args.monitor:
        print("Monitoring task status...")
        monitor_tasks(all_tasks)

if __name__ == "__main__":
    main()
