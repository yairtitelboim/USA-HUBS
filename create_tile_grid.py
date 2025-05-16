#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Create a tile grid for an Area of Interest (AOI).

This script generates a grid of tiles covering the specified AOI,
with each tile having a fixed size in pixels at a given resolution.
The resulting tile grid is saved as a GeoJSON file.
"""

import os
import json
import argparse
from datetime import datetime
import geopandas as gpd
import pandas as pd
from shapely.geometry import box, Polygon, mapping
import numpy as np

# Constants
DEFAULT_TILE_SIZE_PIXELS = 256  # Default tile size in pixels
DEFAULT_RESOLUTION = 10  # Default resolution in meters per pixel (Sentinel-2)
DEFAULT_OUTPUT_DIR = "tiles"  # Default output directory

def create_tile_grid(aoi_geom, tile_size_pixels=DEFAULT_TILE_SIZE_PIXELS,
                    resolution=DEFAULT_RESOLUTION, buffer_percent=0, crs="EPSG:4326"):
    """
    Create a grid of tiles covering the AOI.

    Args:
        aoi_geom: Shapely geometry representing the AOI
        tile_size_pixels: Size of each tile in pixels
        resolution: Resolution in meters per pixel
        buffer_percent: Optional buffer around each tile (as percentage of tile size)
        crs: Coordinate reference system to use if aoi_geom doesn't have one

    Returns:
        GeoDataFrame containing the tile grid
    """
    # Calculate tile size in meters
    tile_size_meters = tile_size_pixels * resolution
    print(f"Tile size: {tile_size_pixels}px × {tile_size_pixels}px at {resolution}m/px = {tile_size_meters}m × {tile_size_meters}m")

    # Get the bounds of the AOI
    minx, miny, maxx, maxy = aoi_geom.bounds
    print(f"AOI bounds: ({minx}, {miny}) to ({maxx}, {maxy})")

    # Calculate the number of tiles in each direction
    num_tiles_x = int(np.ceil((maxx - minx) / tile_size_meters))
    num_tiles_y = int(np.ceil((maxy - miny) / tile_size_meters))
    print(f"Grid size: {num_tiles_x} × {num_tiles_y} = {num_tiles_x * num_tiles_y} tiles")

    # Create the tiles
    tiles = []
    for i in range(num_tiles_x):
        for j in range(num_tiles_y):
            # Calculate tile bounds
            tile_minx = minx + i * tile_size_meters
            tile_miny = miny + j * tile_size_meters
            tile_maxx = min(tile_minx + tile_size_meters, maxx)
            tile_maxy = min(tile_miny + tile_size_meters, maxy)

            # Create tile geometry
            tile_geom = box(tile_minx, tile_miny, tile_maxx, tile_maxy)

            # Apply buffer if specified
            if buffer_percent > 0:
                buffer_size = tile_size_meters * buffer_percent / 100
                tile_geom = tile_geom.buffer(buffer_size)

            # Create tile ID (row_col format)
            tile_id = f"r{j:02d}_c{i:02d}"

            # Add tile to list
            tiles.append({
                "geometry": tile_geom,
                "properties": {
                    "tile_id": tile_id,
                    "row": j,
                    "col": i,
                    "minx": tile_minx,
                    "miny": tile_miny,
                    "maxx": tile_maxx,
                    "maxy": tile_maxy,
                    "width_m": tile_maxx - tile_minx,
                    "height_m": tile_maxy - tile_miny
                }
            })

    # Create GeoDataFrame with appropriate CRS
    # Try to get CRS from aoi_geom, fall back to default if not available
    try:
        geom_crs = aoi_geom.crs
        if geom_crs is None:
            print(f"Warning: No CRS found in AOI geometry. Using default: {crs}")
            tiles_gdf = gpd.GeoDataFrame(tiles, crs=crs)
        else:
            tiles_gdf = gpd.GeoDataFrame(tiles, crs=geom_crs)
    except AttributeError:
        print(f"Warning: No CRS attribute in AOI geometry. Using default: {crs}")
        tiles_gdf = gpd.GeoDataFrame(tiles, crs=crs)

    return tiles_gdf

def load_aoi(aoi_path):
    """
    Load AOI from a file (GeoJSON, Shapefile, etc.)

    Args:
        aoi_path: Path to the AOI file

    Returns:
        Shapely geometry representing the AOI with CRS
    """
    # Check if the file exists
    if not os.path.exists(aoi_path):
        raise FileNotFoundError(f"AOI file not found: {aoi_path}")

    # Use GeoPandas to load the file (works for all formats and preserves CRS)
    gdf = gpd.read_file(aoi_path)

    # If no CRS is set, default to EPSG:4326 (WGS84)
    if gdf.crs is None:
        print("Warning: No CRS found in input file. Assuming EPSG:4326 (WGS84).")
        gdf = gdf.set_crs("EPSG:4326")

    # Use the first geometry
    return gdf.geometry.iloc[0]

def create_bbox_aoi(bbox):
    """
    Create an AOI from a bounding box.

    Args:
        bbox: Bounding box as [minx, miny, maxx, maxy]

    Returns:
        Shapely geometry representing the AOI with CRS
    """
    # Create a GeoDataFrame with the box geometry and set CRS to EPSG:4326 (WGS84)
    geom = box(*bbox)
    gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")
    return gdf.geometry.iloc[0]

def main():
    """Main function to create a tile grid."""
    parser = argparse.ArgumentParser(description="Create a tile grid for an AOI")

    # AOI input options (mutually exclusive)
    aoi_group = parser.add_mutually_exclusive_group(required=True)
    aoi_group.add_argument("--aoi-file", help="Path to AOI file (GeoJSON, Shapefile, etc.)")
    aoi_group.add_argument("--bbox", nargs=4, type=float, help="Bounding box as minx miny maxx maxy")

    # Tile parameters
    parser.add_argument("--tile-size", type=int, default=DEFAULT_TILE_SIZE_PIXELS,
                        help=f"Tile size in pixels (default: {DEFAULT_TILE_SIZE_PIXELS})")
    parser.add_argument("--resolution", type=float, default=DEFAULT_RESOLUTION,
                        help=f"Resolution in meters per pixel (default: {DEFAULT_RESOLUTION})")
    parser.add_argument("--buffer", type=float, default=0,
                        help="Buffer around each tile as percentage of tile size (default: 0)")

    # Output options
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--output-name", default=None,
                        help="Output filename (default: tiles_YYYYMMDD_HHMMSS.geojson)")

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Load or create AOI
    if args.aoi_file:
        aoi_geom = load_aoi(args.aoi_file)
        aoi_source = os.path.basename(args.aoi_file)
    else:
        aoi_geom = create_bbox_aoi(args.bbox)
        aoi_source = f"bbox_{args.bbox[0]}_{args.bbox[1]}_{args.bbox[2]}_{args.bbox[3]}"

    # Create tile grid
    tiles_gdf = create_tile_grid(
        aoi_geom,
        tile_size_pixels=args.tile_size,
        resolution=args.resolution,
        buffer_percent=args.buffer
    )

    # Generate output filename if not specified
    if args.output_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"tiles_{timestamp}.geojson"
    else:
        output_name = args.output_name

    # Ensure output name has .geojson extension
    if not output_name.endswith(".geojson"):
        output_name += ".geojson"

    # Save tile grid to GeoJSON
    output_path = os.path.join(args.output_dir, output_name)
    tiles_gdf.to_file(output_path, driver="GeoJSON")

    # Also save as JSON with simplified structure for EE exports
    tiles_json = []
    for _, row in tiles_gdf.iterrows():
        tiles_json.append({
            "id": row["properties"]["tile_id"],
            "geom": mapping(row["geometry"])
        })

    json_output_path = os.path.join(args.output_dir, output_name.replace(".geojson", ".json"))
    with open(json_output_path, 'w') as f:
        json.dump(tiles_json, f, indent=2)

    print(f"Created {len(tiles_gdf)} tiles")
    print(f"Saved tile grid to {output_path}")
    print(f"Saved simplified JSON for EE exports to {json_output_path}")

if __name__ == "__main__":
    main()
