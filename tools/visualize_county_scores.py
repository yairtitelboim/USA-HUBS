#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Visualize county obsolescence scores.

This script loads county-joined GeoJSON files and creates visualizations of
obsolescence scores per county.
"""

import os
import argparse
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import numpy as np


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


def create_visualization(gdf, output_path, column='obsolescence_score', title=None):
    """
    Create a visualization of county scores.
    
    Args:
        gdf: GeoDataFrame with county polygons and scores
        output_path: Path to save the visualization
        column: Column to visualize
        title: Title for the visualization
        
    Returns:
        Path to the saved visualization
    """
    print(f"Creating visualization for {column}...")
    
    # Create figure and axis
    fig, ax = plt.subplots(1, 1, figsize=(15, 10))
    
    # Create a custom colormap
    cmap = plt.cm.RdBu_r
    
    # Plot counties with scores
    gdf.plot(
        column=column,
        cmap=cmap,
        linewidth=0.5,
        edgecolor='black',
        legend=True,
        ax=ax
    )
    
    # Set title and labels
    if title:
        ax.set_title(title, fontsize=16)
    else:
        ax.set_title(f'{column.replace("_", " ").title()} by County', fontsize=16)
    
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    
    # Save the figure
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Saved visualization to {output_path}")
    
    return output_path


def create_combined_visualization(regions, output_path):
    """
    Create a combined visualization of all regions.
    
    Args:
        regions: Dictionary of region names and GeoDataFrames
        output_path: Path to save the visualization
        
    Returns:
        Path to the saved visualization
    """
    print("Creating combined visualization...")
    
    # Create figure and axes
    fig, axes = plt.subplots(1, len(regions), figsize=(20, 10))
    
    # Create a custom colormap
    cmap = plt.cm.RdBu_r
    
    # Get the min and max values across all regions
    min_val = min([gdf['obsolescence_score'].min() for gdf in regions.values()])
    max_val = max([gdf['obsolescence_score'].max() for gdf in regions.values()])
    
    # Create a normalization for the colormap
    norm = colors.Normalize(vmin=min_val, vmax=max_val)
    
    # Plot each region
    for i, (region, gdf) in enumerate(regions.items()):
        ax = axes[i]
        
        # Plot counties with scores
        gdf.plot(
            column='obsolescence_score',
            cmap=cmap,
            norm=norm,
            linewidth=0.5,
            edgecolor='black',
            legend=True,
            ax=ax
        )
        
        # Set title and labels
        ax.set_title(f'{region.title()} Region', fontsize=16)
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
    
    # Add a title to the figure
    fig.suptitle('Obsolescence Score by County Across Regions', fontsize=20)
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    # Save the figure
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Saved combined visualization to {output_path}")
    
    return output_path


def main():
    """Main function to visualize county scores."""
    parser = argparse.ArgumentParser(description="Visualize county obsolescence scores")
    
    # Required arguments
    parser.add_argument("--regions", nargs='+', required=True,
                        help="List of regions to visualize (e.g., south west east)")
    parser.add_argument("--output-dir", required=True,
                        help="Directory to save the visualizations")
    
    # Optional arguments
    parser.add_argument("--combined", action="store_true",
                        help="Create a combined visualization of all regions")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load county GeoJSON files for each region
    regions = {}
    for region in args.regions:
        geojson_path = f"data/{region}/county_joined.geojson"
        
        # Check if the file exists
        if not os.path.exists(geojson_path):
            print(f"County GeoJSON file not found: {geojson_path}")
            print(f"Skipping region: {region}")
            continue
        
        # Load the GeoJSON file
        gdf = load_county_geojson(geojson_path)
        
        # Add to the dictionary
        regions[region] = gdf
        
        # Create visualization for the region
        output_path = os.path.join(args.output_dir, f"{region}_counties.png")
        create_visualization(
            gdf,
            output_path,
            title=f'Obsolescence Score by County - {region.title()} Region'
        )
    
    # Create combined visualization if requested
    if args.combined and len(regions) > 0:
        output_path = os.path.join(args.output_dir, "combined_counties.png")
        create_combined_visualization(regions, output_path)
    
    print("Done!")


if __name__ == "__main__":
    main()
