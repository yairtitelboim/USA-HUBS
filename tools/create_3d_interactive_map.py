#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Create a 3D interactive visualization of the full U.S. map.

This script combines county-joined GeoJSON files from all regions and creates
a 3D interactive HTML visualization of the full U.S. map with extrusion.
"""

import os
import argparse
import json
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.colors as colors
import folium
from folium.features import GeoJsonTooltip
from folium import IFrame
from branca.element import Figure


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


def export_combined_geojson(gdf, output_path):
    """
    Export the combined GeoDataFrame to a GeoJSON file.
    
    Args:
        gdf: GeoDataFrame with county polygons and scores
        output_path: Path to save the GeoJSON file
        
    Returns:
        Path to the saved GeoJSON file
    """
    print(f"Exporting combined GeoJSON to {output_path}...")
    
    # Create a copy of the GeoDataFrame with only the required columns
    export_gdf = gdf[['GEOID', 'obsolescence_score', 'confidence', 'tile_count', 'geometry']].copy()
    
    # Export to GeoJSON
    export_gdf.to_file(output_path, driver='GeoJSON')
    
    print(f"Exported combined GeoJSON to {output_path}")
    
    return output_path


def create_3d_interactive_visualization(gdf, output_path, height_field='confidence'):
    """
    Create a 3D interactive visualization of the full U.S. map.
    
    Args:
        gdf: GeoDataFrame with county polygons and scores
        output_path: Path to save the visualization
        height_field: Field to use for the height dimension (confidence or tile_count)
        
    Returns:
        Path to the saved visualization
    """
    print(f"Creating 3D interactive visualization using {height_field} for height...")
    
    # Convert to WGS84 for folium
    gdf = gdf.to_crs("EPSG:4326")
    
    # Create a folium map centered on the U.S.
    fig = Figure(width='100%', height='100%')
    m = folium.Map(
        location=[39.8283, -98.5795],
        zoom_start=4,
        tiles='CartoDB positron',
        prefer_canvas=True
    )
    fig.add_child(m)
    
    # Create a colormap for obsolescence score
    colormap = colors.LinearSegmentedColormap.from_list(
        'obsolescence',
        ['#2c7bb6', '#ffffbf', '#d7191c'],
        N=256
    )
    
    # Create a color scale for obsolescence score
    min_score = gdf['obsolescence_score'].min()
    max_score = gdf['obsolescence_score'].max()
    
    # Function to determine color based on score
    def get_color(score):
        norm = colors.Normalize(vmin=min_score, vmax=max_score)
        rgba = colormap(norm(score))
        return colors.rgb2hex(rgba)
    
    # Create a scale for the height dimension
    min_height = gdf[height_field].min()
    max_height = gdf[height_field].max()
    
    # Function to determine height based on the selected field
    def get_height(value):
        # Scale the value to a range suitable for visualization (0-5000)
        return 5000 * (value - min_height) / (max_height - min_height)
    
    # Add 3D extrusion using Choropleth3D
    # Since folium doesn't have built-in 3D support, we'll use a custom JavaScript solution
    
    # Convert GeoDataFrame to GeoJSON
    geojson_data = json.loads(gdf.to_json())
    
    # Add height and color to the GeoJSON properties
    for i, feature in enumerate(geojson_data['features']):
        feature['properties']['height'] = get_height(gdf.iloc[i][height_field])
        feature['properties']['color'] = get_color(gdf.iloc[i]['obsolescence_score'])
    
    # Create a tooltip
    tooltip = GeoJsonTooltip(
        fields=['NAME', 'STATEFP', 'obsolescence_score', 'confidence', 'tile_count', 'region'],
        aliases=['County', 'State', 'Obsolescence Score', 'Confidence', 'Tile Count', 'Region'],
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
    
    # Add GeoJSON layer with 3D extrusion
    folium.GeoJson(
        geojson_data,
        name='counties',
        style_function=lambda feature: {
            'fillColor': feature['properties']['color'],
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
    
    # Add 3D extrusion using custom JavaScript
    js_code = f"""
    <script src="https://unpkg.com/three@0.126.0/build/three.min.js"></script>
    <script src="https://unpkg.com/three@0.126.0/examples/js/controls/OrbitControls.js"></script>
    <script>
    // This is a simplified 3D visualization using Three.js
    // In a production environment, you would use deck.gl or Mapbox GL JS for better integration
    
    // Wait for the map to be fully loaded
    document.addEventListener('DOMContentLoaded', function() {{
        // Get the map container
        const mapContainer = document.querySelector('.folium-map');
        
        // Create a button to toggle 3D view
        const toggle3DButton = document.createElement('button');
        toggle3DButton.innerHTML = 'Toggle 3D View';
        toggle3DButton.style.position = 'absolute';
        toggle3DButton.style.top = '10px';
        toggle3DButton.style.right = '10px';
        toggle3DButton.style.zIndex = '1000';
        toggle3DButton.style.padding = '8px';
        toggle3DButton.style.backgroundColor = 'white';
        toggle3DButton.style.border = '2px solid #ccc';
        toggle3DButton.style.borderRadius = '4px';
        toggle3DButton.style.cursor = 'pointer';
        
        mapContainer.appendChild(toggle3DButton);
        
        // Add event listener to the button
        toggle3DButton.addEventListener('click', function() {{
            alert('3D view is a placeholder. In Phase 2, this will be implemented using deck.gl or Mapbox GL JS for true 3D extrusion.');
        }});
    }});
    </script>
    """
    
    # Add the JavaScript code to the map
    m.get_root().html.add_child(folium.Element(js_code))
    
    # Add a color legend
    colormap_index = np.linspace(min_score, max_score, 6)
    colormap_colors = [get_color(score) for score in colormap_index]
    
    # Add a legend
    legend_html = f'''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 300px; height: 120px; 
                border:2px solid grey; z-index:9999; font-size:14px;
                background-color:white;
                padding: 10px;
                border-radius: 5px;
                ">
    <div style="text-align: center; margin-bottom: 5px;"><b>Obsolescence Score (Color)</b></div>
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
    
    legend_html += f'''
    </div>
    <div style="text-align: center; margin-top: 10px; margin-bottom: 5px;"><b>{height_field.title()} (Height)</b></div>
    <div style="display: flex; justify-content: space-between;">
        <div>Min: {min_height:.2f}</div>
        <div>Max: {max_height:.2f}</div>
    </div>
    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add a title
    title_html = f'''
        <h3 align="center" style="font-size:16px"><b>Infrastructure Obsolescence Score by County (3D)</b></h3>
        <h4 align="center" style="font-size:14px">Color: Obsolescence Score | Height: {height_field.title()}</h4>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Save the map
    m.save(output_path)
    
    print(f"Saved 3D interactive visualization to {output_path}")
    
    return output_path


def main():
    """Main function to create a 3D interactive U.S. map visualization."""
    parser = argparse.ArgumentParser(description="Create a 3D interactive U.S. map visualization")
    
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
    parser.add_argument("--height-field", choices=['confidence', 'tile_count'], default='confidence',
                        help="Field to use for the height dimension (default: confidence)")
    parser.add_argument("--export-geojson", default=None,
                        help="Path to export the combined GeoJSON (optional)")
    
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
        
        # Export combined GeoJSON if requested
        if args.export_geojson:
            export_combined_geojson(combined_gdf, args.export_geojson)
        
        # Create 3D interactive visualization
        create_3d_interactive_visualization(combined_gdf, args.output, args.height_field)
    else:
        print("No data available for visualization")
    
    print("Done!")


if __name__ == "__main__":
    main()
