#!/usr/bin/env python3
"""
Fix county boundaries in the county_scores.geojson file.

This script:
1. Loads the county_scores.geojson file
2. Loads the county shapefile
3. Replaces the simplified rectangular geometries with actual county boundaries
4. Creates a new GeoJSON file with the actual county boundaries and the scores data
"""

import json
import geopandas as gpd
import pandas as pd
import os
import logging
from shapely.geometry import shape, mapping

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_county_scores(geojson_path):
    """Load county scores from GeoJSON file."""
    try:
        # Read the file line by line to handle potential JSON parsing errors
        with open(geojson_path, 'r') as f:
            content = f.read()
            
        # Try to parse the JSON
        try:
            data = json.loads(content)
            logger.info(f"Successfully loaded {len(data['features'])} features from {geojson_path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            
            # Try to fix the JSON by removing the problematic parts
            logger.info("Attempting to fix the JSON...")
            
            # Start with the basic structure
            fixed_content = '{"type":"FeatureCollection","features":['
            
            # Extract individual features
            import re
            feature_pattern = r'{"type":"Feature"[^}]+}}},'
            features = re.findall(feature_pattern, content)
            
            if not features:
                logger.error("Could not extract features from the file")
                return None
                
            # Join the features
            fixed_content += ''.join(features)
            
            # Remove the trailing comma and close the JSON
            if fixed_content.endswith(','):
                fixed_content = fixed_content[:-1]
            fixed_content += ']}'
            
            # Try to parse the fixed JSON
            try:
                data = json.loads(fixed_content)
                logger.info(f"Successfully loaded {len(data['features'])} features from fixed JSON")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to fix JSON: {e}")
                return None
    except Exception as e:
        logger.error(f"Error loading county scores: {e}")
        return None

def load_county_shapefile(shapefile_path):
    """Load county boundaries from shapefile."""
    try:
        gdf = gpd.read_file(shapefile_path)
        logger.info(f"Loaded {len(gdf)} county boundaries from {shapefile_path}")
        return gdf
    except Exception as e:
        logger.error(f"Error loading county shapefile: {e}")
        return None

def fix_county_boundaries(county_scores, county_boundaries):
    """Replace simplified geometries with actual county boundaries."""
    if county_scores is None or county_boundaries is None:
        logger.error("Cannot fix boundaries: missing data")
        return None
        
    # Create a lookup dictionary for county boundaries by GEOID
    boundary_lookup = {row['GEOID']: row['geometry'] for _, row in county_boundaries.iterrows()}
    
    # Count how many geometries we replace
    replaced_count = 0
    
    # Replace geometries in county_scores
    for feature in county_scores['features']:
        geoid = feature['properties'].get('GEOID')
        if geoid and geoid in boundary_lookup:
            # Replace the geometry with the actual county boundary
            feature['geometry'] = mapping(boundary_lookup[geoid])
            replaced_count += 1
    
    logger.info(f"Replaced {replaced_count} geometries out of {len(county_scores['features'])} features")
    
    return county_scores

def save_fixed_geojson(data, output_path):
    """Save fixed data as GeoJSON."""
    try:
        with open(output_path, 'w') as f:
            json.dump(data, f)
        
        logger.info(f"Saved fixed data to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving fixed GeoJSON: {e}")
        return False

def main():
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    county_scores_path = os.path.join(base_dir, 'data', 'final', 'county_scores.geojson')
    shapefile_path = os.path.join(base_dir, 'data', 'tl_2024_us_county', 'tl_2024_us_county.shp')
    output_path = os.path.join(base_dir, 'data', 'final', 'fixed_county_scores.geojson')
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Load data
    logger.info("Loading county scores data...")
    county_scores = load_county_scores(county_scores_path)
    
    logger.info("Loading county shapefile...")
    county_boundaries = load_county_shapefile(shapefile_path)
    
    # Fix county boundaries
    logger.info("Fixing county boundaries...")
    fixed_data = fix_county_boundaries(county_scores, county_boundaries)
    
    if fixed_data:
        # Save fixed data
        logger.info("Saving fixed data...")
        success = save_fixed_geojson(fixed_data, output_path)
        
        if success:
            # Update the HTML file to use the new fixed data
            html_file_path = os.path.join(base_dir, 'mapbox_shapefile_counties.html')
            if os.path.exists(html_file_path):
                logger.info(f"Updating HTML file to use fixed data: {html_file_path}")
                with open(html_file_path, 'r') as f:
                    html_content = f.read()
                
                # Replace the data source path
                html_content = html_content.replace(
                    "fetch('data/final/county_scores.geojson')",
                    "fetch('data/final/fixed_county_scores.geojson')"
                )
                
                # Save the updated HTML file
                with open(html_file_path, 'w') as f:
                    f.write(html_content)
                logger.info("HTML file updated successfully")
    
    logger.info("Done!")

if __name__ == "__main__":
    main()
