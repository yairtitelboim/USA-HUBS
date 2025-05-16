#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Aggregate tile-level results to U.S. county polygons.

This script joins tile-level scores to county polygons and aggregates the scores
per county, outputting a GeoJSON with obsolescence scores per county.
"""

import os
import argparse
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import numpy as np
import matplotlib.pyplot as plt


def load_tile_scores(tile_scores_path):
    """
    Load tile scores from a CSV file.
    
    Args:
        tile_scores_path: Path to the tile scores CSV file
        
    Returns:
        GeoDataFrame with tile scores and geometries
    """
    print(f"Loading tile scores from {tile_scores_path}...")
    
    # Read the CSV file
    df = pd.read_csv(tile_scores_path)
    
    # Create geometries from longitude and latitude
    geometries = [Point(lon, lat) for lon, lat in zip(df['longitude'], df['latitude'])]
    
    # Create a GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry=geometries, crs="EPSG:4326")
    
    print(f"Loaded {len(gdf)} tiles with scores")
    
    return gdf


def load_county_shapefile(county_shp_path):
    """
    Load county shapefile.
    
    Args:
        county_shp_path: Path to the county shapefile
        
    Returns:
        GeoDataFrame with county polygons
    """
    print(f"Loading county shapefile from {county_shp_path}...")
    
    # Read the shapefile
    counties = gpd.read_file(county_shp_path)
    
    print(f"Loaded {len(counties)} counties")
    
    return counties


def join_tiles_to_counties(tiles_gdf, counties_gdf):
    """
    Join tiles to counties using spatial join.
    
    Args:
        tiles_gdf: GeoDataFrame with tile scores and geometries
        counties_gdf: GeoDataFrame with county polygons
        
    Returns:
        GeoDataFrame with tiles joined to counties
    """
    print("Joining tiles to counties...")
    
    # Ensure both GeoDataFrames have the same CRS
    if tiles_gdf.crs != counties_gdf.crs:
        print(f"Reprojecting tiles from {tiles_gdf.crs} to {counties_gdf.crs}")
        tiles_gdf = tiles_gdf.to_crs(counties_gdf.crs)
    
    # Perform spatial join
    joined = gpd.sjoin(tiles_gdf, counties_gdf, how="inner", predicate="within")
    
    print(f"Joined {len(joined)} tiles to counties")
    
    return joined


def aggregate_scores_by_county(joined_gdf, counties_gdf):
    """
    Aggregate scores by county.
    
    Args:
        joined_gdf: GeoDataFrame with tiles joined to counties
        counties_gdf: GeoDataFrame with county polygons
        
    Returns:
        GeoDataFrame with county polygons and aggregated scores
    """
    print("Aggregating scores by county...")
    
    # Group by county GEOID and calculate mean scores
    grouped = joined_gdf.groupby('GEOID').agg({
        'obsolescence_score': 'mean',
        'confidence': 'mean',
        'tile_id': 'count'
    }).reset_index()
    
    # Rename the tile_id count column
    grouped = grouped.rename(columns={'tile_id': 'tile_count'})
    
    # Merge with county polygons
    merged = counties_gdf.merge(grouped, on='GEOID', how='left')
    
    # Fill NaN values (counties with no tiles)
    merged['obsolescence_score'] = merged['obsolescence_score'].fillna(0)
    merged['confidence'] = merged['confidence'].fillna(0)
    merged['tile_count'] = merged['tile_count'].fillna(0)
    
    print(f"Aggregated scores for {len(grouped)} counties")
    
    return merged


def create_visualization(county_scores_gdf, output_path):
    """
    Create a visualization of county scores.
    
    Args:
        county_scores_gdf: GeoDataFrame with county polygons and scores
        output_path: Path to save the visualization
        
    Returns:
        Path to the saved visualization
    """
    print("Creating visualization...")
    
    # Create figure and axis
    fig, ax = plt.subplots(1, 1, figsize=(15, 10))
    
    # Plot counties with scores
    county_scores_gdf.plot(
        column='obsolescence_score',
        cmap='RdBu_r',
        linewidth=0.5,
        edgecolor='black',
        legend=True,
        ax=ax
    )
    
    # Set title and labels
    ax.set_title('Obsolescence Score by County', fontsize=16)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    
    # Save the figure
    viz_path = os.path.splitext(output_path)[0] + '_viz.png'
    plt.savefig(viz_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Saved visualization to {viz_path}")
    
    return viz_path


def main():
    """Main function to aggregate tile scores to counties."""
    parser = argparse.ArgumentParser(description="Aggregate tile scores to counties")
    
    # Required arguments
    parser.add_argument("--tile-scores", required=True, help="Path to the tile scores CSV file")
    parser.add_argument("--county-shp", required=True, help="Path to the county shapefile")
    parser.add_argument("--output", required=True, help="Path to save the output GeoJSON file")
    
    # Optional arguments
    parser.add_argument("--visualize", action="store_true", help="Create a visualization of county scores")
    
    args = parser.parse_args()
    
    # Load tile scores
    tiles_gdf = load_tile_scores(args.tile_scores)
    
    # Load county shapefile
    counties_gdf = load_county_shapefile(args.county_shp)
    
    # Join tiles to counties
    joined_gdf = join_tiles_to_counties(tiles_gdf, counties_gdf)
    
    # Aggregate scores by county
    county_scores_gdf = aggregate_scores_by_county(joined_gdf, counties_gdf)
    
    # Save the output GeoJSON
    print(f"Saving county scores to {args.output}...")
    county_scores_gdf.to_file(args.output, driver="GeoJSON")
    print(f"Saved county scores to {args.output}")
    
    # Create visualization if requested
    if args.visualize:
        create_visualization(county_scores_gdf, args.output)
    
    print("Done!")


if __name__ == "__main__":
    main()
