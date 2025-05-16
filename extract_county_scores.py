#!/usr/bin/env python3
"""
Extract county scores from a potentially corrupted GeoJSON file.

This script:
1. Reads the county_scores.geojson file line by line
2. Extracts county data (GEOID, scores, etc.)
3. Creates a clean CSV file with the extracted data
4. Merges this data with the county shapefile
5. Creates a new GeoJSON file with the actual county boundaries and the scores data
"""

import json
import geopandas as gpd
import pandas as pd
import os
import re
import logging
from shapely.geometry import shape

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_county_data(geojson_path):
    """Extract county data from a potentially corrupted GeoJSON file."""
    county_data = []
    
    try:
        # First try to read the file line by line
        with open(geojson_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                # Look for lines that contain county data
                if '"GEOID"' in line and '"obsolescence_score"' in line:
                    try:
                        # Extract the properties object using regex
                        props_match = re.search(r'"properties":\s*({[^}]+})', line)
                        if props_match:
                            props_str = props_match.group(1)
                            # Fix any JSON syntax issues
                            props_str = props_str.replace('""', '"null"')
                            props_str = props_str.replace('NaT', '"NaT"')
                            # Add quotes around property names if missing
                            props_str = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', props_str)
                            # Try to parse the properties
                            try:
                                props = json.loads(props_str)
                                county_data.append(props)
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse properties on line {line_num}: {e}")
                    except Exception as e:
                        logger.warning(f"Error processing line {line_num}: {e}")
        
        logger.info(f"Extracted data for {len(county_data)} counties")
        return county_data
    
    except Exception as e:
        logger.error(f"Error extracting county data: {e}")
        raise

def load_county_shapefile(shapefile_path):
    """Load county boundaries from shapefile."""
    try:
        gdf = gpd.read_file(shapefile_path)
        logger.info(f"Loaded {len(gdf)} county boundaries from {shapefile_path}")
        return gdf
    except Exception as e:
        logger.error(f"Error loading county shapefile: {e}")
        raise

def merge_data(county_boundaries, county_data):
    """Merge county boundaries with scores data."""
    # Create a DataFrame from the county data
    county_df = pd.DataFrame(county_data)
    
    # Create a copy of the county boundaries GeoDataFrame
    merged_gdf = county_boundaries.copy()
    
    # Merge data based on GEOID
    if 'GEOID' in county_df.columns:
        # Create a lookup dictionary for faster access
        county_lookup = {row['GEOID']: row for _, row in county_df.iterrows() if pd.notna(row.get('GEOID'))}
        
        # Add columns for scores
        for col in ['obsolescence_score', 'growth_potential_score', 'confidence', 'tile_count', 
                   'ndvi_value', 'ndbi_value', 'bsi_value']:
            if col in county_df.columns:
                merged_gdf[col] = None
        
        # Count matches
        match_count = 0
        
        # Merge data based on GEOID
        for idx, row in merged_gdf.iterrows():
            geoid = row['GEOID']
            if geoid in county_lookup:
                match_count += 1
                props = county_lookup[geoid]
                for col in ['obsolescence_score', 'growth_potential_score', 'confidence', 'tile_count', 
                           'ndvi_value', 'ndbi_value', 'bsi_value']:
                    if col in props and col in merged_gdf.columns:
                        merged_gdf.at[idx, col] = props.get(col)
        
        logger.info(f"Matched {match_count} counties out of {len(merged_gdf)}")
        
        # Filter to only include counties with scores
        scored_gdf = merged_gdf[merged_gdf['obsolescence_score'].notnull()]
        logger.info(f"Filtered to {len(scored_gdf)} counties with scores")
        
        return scored_gdf
    else:
        logger.error("No GEOID column found in county data")
        return None

def save_merged_geojson(gdf, output_path):
    """Save merged data as GeoJSON."""
    try:
        # Convert to GeoJSON
        geojson_data = json.loads(gdf.to_json())
        
        # Add county_name and state_name properties for compatibility
        for feature in geojson_data['features']:
            props = feature['properties']
            props['county_name'] = props.get('NAME')
            props['state_name'] = props.get('STATE')
            props['county_fips'] = props.get('GEOID')
            props['state_fips'] = props.get('STATEFP')
        
        # Save to file
        with open(output_path, 'w') as f:
            json.dump(geojson_data, f)
        
        logger.info(f"Saved merged data to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving merged GeoJSON: {e}")
        raise

def main():
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    county_scores_path = os.path.join(base_dir, 'data', 'final', 'county_scores.geojson')
    shapefile_path = os.path.join(base_dir, 'data', 'tl_2024_us_county', 'tl_2024_us_county.shp')
    output_path = os.path.join(base_dir, 'data', 'final', 'merged_county_scores.geojson')
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Extract county data
    logger.info("Extracting county data...")
    county_data = extract_county_data(county_scores_path)
    
    # Load county shapefile
    logger.info("Loading county shapefile...")
    county_boundaries = load_county_shapefile(shapefile_path)
    
    # Merge data
    logger.info("Merging data...")
    merged_data = merge_data(county_boundaries, county_data)
    
    if merged_data is not None:
        # Save merged data
        logger.info("Saving merged data...")
        save_merged_geojson(merged_data, output_path)
        
        # Update the HTML file to use the new merged data
        html_file_path = os.path.join(base_dir, 'mapbox_shapefile_counties.html')
        if os.path.exists(html_file_path):
            logger.info(f"Updating HTML file to use merged data: {html_file_path}")
            with open(html_file_path, 'r') as f:
                html_content = f.read()
            
            # Replace the data source path
            html_content = html_content.replace(
                "fetch('data/final/county_scores.geojson')",
                "fetch('data/final/merged_county_scores.geojson')"
            )
            
            # Save the updated HTML file
            with open(html_file_path, 'w') as f:
                f.write(html_content)
            logger.info("HTML file updated successfully")
    
    logger.info("Done!")

if __name__ == "__main__":
    main()
