#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Create an interactive visualization of the full U.S. map.

This script combines county-joined GeoJSON files from all regions and creates
an interactive HTML visualization of the full U.S. map.
"""

import os
import argparse
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.colors as colors
import folium
from folium.features import GeoJsonTooltip


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


def create_interactive_visualization(gdf, output_path):
    """
    Create an interactive visualization of the full U.S. map.
    
    Args:
        gdf: GeoDataFrame with county polygons and scores
        output_path: Path to save the visualization
        
    Returns:
        Path to the saved visualization
    """
    print("Creating interactive visualization...")
    
    # Convert to WGS84 for folium
    gdf = gdf.to_crs("EPSG:4326")
    
    # Create a folium map centered on the U.S.
    m = folium.Map(
        location=[39.8283, -98.5795],
        zoom_start=4,
        tiles='CartoDB positron'
    )
    
    # Create a colormap
    colormap = colors.LinearSegmentedColormap.from_list(
        'obsolescence',
        ['#2c7bb6', '#ffffbf', '#d7191c'],
        N=256
    )
    
    # Create a color scale
    min_score = gdf['obsolescence_score'].min()
    max_score = gdf['obsolescence_score'].max()
    
    # Function to determine color based on score
    def get_color(score):
        norm = colors.Normalize(vmin=min_score, vmax=max_score)
        rgba = colormap(norm(score))
        return colors.rgb2hex(rgba)
    
    # Create a tooltip
    tooltip = GeoJsonTooltip(
        fields=['NAME', 'STATEFP', 'obsolescence_score', 'confidence', 'region'],
        aliases=['County', 'State', 'Obsolescence Score', 'Confidence', 'Region'],
        localize=True,
        sticky=False,
        labels=True,
        style="""
            background-color: #F0EFEF;
            border: 2px solid black;
            border-radius: 3px;
            box-shadow: 3px;
        """,
        max_width=800,
    )
    
    # Add GeoJSON layer
    folium.GeoJson(
        gdf,
        style_function=lambda feature: {
            'fillColor': get_color(feature['properties']['obsolescence_score']),
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7
        },
        tooltip=tooltip,
        highlight_function=lambda feature: {
            'weight': 3,
            'fillOpacity': 0.9
        }
    ).add_to(m)
    
    # Add a color legend
    colormap_index = np.linspace(min_score, max_score, 6)
    colormap_colors = [get_color(score) for score in colormap_index]
    
    # Create a colormap legend
    colormap_caption = 'Obsolescence Score'
    
    # Add a legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 250px; height: 90px; 
                border:2px solid grey; z-index:9999; font-size:14px;
                background-color:white;
                padding: 10px;
                border-radius: 5px;
                ">
    <div style="text-align: center; margin-bottom: 5px;"><b>Obsolescence Score</b></div>
    <div style="display: flex; justify-content: space-between;">
    '''
    
    # Add color boxes
    for i, score in enumerate(colormap_index):
        color = colormap_colors[i]
        legend_html += f'''
        <div style="display: inline-block; width: 30px; height: 15px; 
                    background-color: {color}; margin-right: 5px;"></div>
        '''
    
    legend_html += '''
    </div>
    <div style="display: flex; justify-content: space-between;">
    '''
    
    # Add labels
    for score in colormap_index:
        legend_html += f'''
        <div style="display: inline-block; width: 30px; text-align: center; 
                    margin-right: 5px;">{score:.1f}</div>
        '''
    
    legend_html += '''
    </div>
    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add a title
    title_html = '''
        <h3 align="center" style="font-size:16px"><b>Infrastructure Obsolescence Score by County</b></h3>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Save the map
    m.save(output_path)
    
    print(f"Saved interactive visualization to {output_path}")
    
    return output_path


def main():
    """Main function to create an interactive U.S. map visualization."""
    parser = argparse.ArgumentParser(description="Create an interactive U.S. map visualization")
    
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
        
        # Create interactive visualization
        create_interactive_visualization(combined_gdf, args.output)
    else:
        print("No data available for visualization")
    
    print("Done!")


if __name__ == "__main__":
    main()
