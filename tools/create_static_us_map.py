#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Create a static visualization of the full U.S. map.

This script combines county-joined GeoJSON files from all regions and creates
a static PNG visualization of the full U.S. map.
"""

import os
import argparse
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors


def load_county_geojson(geojson_path):
    """
    Load county GeoJSON file.
    
    Args:
        geojson_path: Path to the county GeoJSON file
        
    Returns:
        GeoDataFrame with county polygons and scores
    """
    print(f"Loading county GeoJSON from {geojson_path}...")
    
    # Read the GeoJSON file
    gdf = gpd.read_file(geojson_path)
    
    print(f"Loaded {len(gdf)} counties with scores")
    
    return gdf


def generate_mock_data(gdf, region):
    """
    Generate mock data for counties without scores.
    
    Args:
        gdf: GeoDataFrame with county polygons
        region: Region name (south, west, east)
        
    Returns:
        GeoDataFrame with mock scores
    """
    print(f"Generating mock data for {region} region...")
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # Generate random scores based on region
    if region == 'south':
        # South region has higher scores (more obsolescence)
        gdf['obsolescence_score'] = np.random.uniform(0.6, 0.9, len(gdf))
    elif region == 'west':
        # West region has medium scores
        gdf['obsolescence_score'] = np.random.uniform(0.4, 0.7, len(gdf))
    else:  # east
        # East region has lower scores (less obsolescence)
        gdf['obsolescence_score'] = np.random.uniform(0.2, 0.5, len(gdf))
    
    # Generate random confidence values
    gdf['confidence'] = np.random.uniform(0.7, 0.95, len(gdf))
    
    # Generate random tile counts
    gdf['tile_count'] = np.random.randint(5, 20, len(gdf))
    
    # Add region column
    gdf['region'] = region
    
    return gdf


def create_static_visualization(gdf, output_path):
    """
    Create a static visualization of the full U.S. map.
    
    Args:
        gdf: GeoDataFrame with county polygons and scores
        output_path: Path to save the visualization
        
    Returns:
        Path to the saved visualization
    """
    print("Creating static visualization...")
    
    # Create figure and axis
    fig, ax = plt.subplots(1, 1, figsize=(20, 12))
    
    # Create a custom colormap
    cmap = plt.cm.RdYlBu_r
    
    # Plot counties with scores
    gdf.plot(
        column='obsolescence_score',
        cmap=cmap,
        linewidth=0.2,
        edgecolor='black',
        legend=True,
        ax=ax,
        legend_kwds={
            'label': 'Obsolescence Score',
            'orientation': 'horizontal',
            'shrink': 0.8,
            'pad': 0.01,
            'aspect': 40
        }
    )
    
    # Set title and labels
    ax.set_title('Infrastructure Obsolescence Score by County', fontsize=20)
    ax.set_xlabel('Longitude', fontsize=14)
    ax.set_ylabel('Latitude', fontsize=14)
    
    # Add a text box with summary statistics
    stats_text = (
        f"Summary Statistics:\n"
        f"Total Counties: {len(gdf)}\n"
        f"Average Score: {gdf['obsolescence_score'].mean():.2f}\n"
        f"High Risk Counties (>0.7): {len(gdf[gdf['obsolescence_score'] > 0.7])}"
    )
    props = dict(boxstyle='round', facecolor='white', alpha=0.7)
    ax.text(0.02, 0.05, stats_text, transform=ax.transAxes, fontsize=12,
            verticalalignment='bottom', bbox=props)
    
    # Save the figure
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Saved static visualization to {output_path}")
    
    return output_path


def main():
    """Main function to create a static U.S. map visualization."""
    parser = argparse.ArgumentParser(description="Create a static U.S. map visualization")
    
    # Required arguments
    parser.add_argument("--output", required=True,
                        help="Path to save the visualization")
    
    # Optional arguments
    parser.add_argument("--regions", nargs='+', default=['south', 'west', 'east'],
                        help="List of regions to include (default: south west east)")
    parser.add_argument("--use-mock-data", action="store_true",
                        help="Use mock data for counties without scores")
    parser.add_argument("--county-shp", default="data/tl_2024_us_county/tl_2024_us_county.shp",
                        help="Path to the county shapefile (for mock data)")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Load county GeoJSON files for each region
    gdfs = []
    for region in args.regions:
        geojson_path = f"data/{region}/county_joined.geojson"
        
        # Check if the file exists
        if not os.path.exists(geojson_path):
            print(f"County GeoJSON file not found: {geojson_path}")
            if args.use_mock_data:
                print(f"Using mock data for {region} region")
                # Load the county shapefile
                if os.path.exists(args.county_shp):
                    gdf = gpd.read_file(args.county_shp)
                    # Generate mock data
                    gdf = generate_mock_data(gdf, region)
                    gdfs.append(gdf)
                else:
                    print(f"County shapefile not found: {args.county_shp}")
                    print(f"Skipping region: {region}")
            else:
                print(f"Skipping region: {region}")
            continue
        
        # Load the GeoJSON file
        gdf = load_county_geojson(geojson_path)
        
        # Add region column if it doesn't exist
        if 'region' not in gdf.columns:
            gdf['region'] = region
        
        # Add to the list
        gdfs.append(gdf)
    
    # Combine all GeoDataFrames
    if len(gdfs) > 0:
        combined_gdf = pd.concat(gdfs)
        print(f"Combined {len(combined_gdf)} counties from {len(gdfs)} regions")
        
        # Create static visualization
        create_static_visualization(combined_gdf, args.output)
    else:
        print("No data available for visualization")
    
    print("Done!")


if __name__ == "__main__":
    main()
