#!/usr/bin/env python3
"""
Recreate a GeoJSON file from the county shapefile and add obsolescence scores from the existing file.
This is a more robust approach to fix a corrupted GeoJSON file.
"""

import os
import sys
import json
import geopandas as gpd
import pandas as pd
import logging
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/recreate_geojson.log')
    ]
)
logger = logging.getLogger(__name__)

def extract_valid_features(input_file):
    """
    Extract valid features from a corrupted GeoJSON file.
    
    Args:
        input_file: Path to the corrupted GeoJSON file
        
    Returns:
        Dictionary mapping GEOID to properties
    """
    logger.info(f"Extracting valid features from {input_file}")
    
    # Dictionary to store GEOID -> properties mapping
    geoid_to_properties = {}
    
    try:
        # Read the file as text
        with open(input_file, 'r') as f:
            content = f.read()
        
        # Find the start of the features array
        features_start = content.find('"features": [') + len('"features": [')
        
        # Extract the features part
        features_content = content[features_start:].strip()
        
        # Remove the closing brackets if they exist
        if features_content.endswith(']}'):
            features_content = features_content[:-2]
        
        # Split by feature delimiter
        feature_strings = features_content.split('},{')
        
        # Process each feature
        for i, feature_str in enumerate(tqdm(feature_strings, desc="Processing features")):
            try:
                # Add the braces back
                if not feature_str.startswith('{'):
                    feature_str = '{' + feature_str
                if not feature_str.endswith('}'):
                    feature_str = feature_str + '}'
                
                # Try to parse it
                feature = json.loads(feature_str)
                
                # Extract GEOID and properties
                if 'properties' in feature and 'GEOID' in feature['properties']:
                    geoid = feature['properties']['GEOID']
                    geoid_to_properties[geoid] = feature['properties']
            except json.JSONDecodeError:
                # Try to extract GEOID and properties manually
                try:
                    # Find the GEOID
                    geoid_start = feature_str.find('"GEOID": "') + len('"GEOID": "')
                    geoid_end = feature_str.find('"', geoid_start)
                    geoid = feature_str[geoid_start:geoid_end]
                    
                    # Find the obsolescence score
                    score_start = feature_str.find('"obsolescence_score": ') + len('"obsolescence_score": ')
                    score_end = feature_str.find(',', score_start)
                    if score_end == -1:  # Might be the last property
                        score_end = feature_str.find('}', score_start)
                    score = float(feature_str[score_start:score_end])
                    
                    # Find the confidence
                    conf_start = feature_str.find('"confidence": ') + len('"confidence": ')
                    conf_end = feature_str.find(',', conf_start)
                    if conf_end == -1:  # Might be the last property
                        conf_end = feature_str.find('}', conf_start)
                    confidence = float(feature_str[conf_start:conf_end])
                    
                    # Find the tile count
                    tile_start = feature_str.find('"tile_count": ') + len('"tile_count": ')
                    tile_end = feature_str.find(',', tile_start)
                    if tile_end == -1:  # Might be the last property
                        tile_end = feature_str.find('}', tile_start)
                    tile_count = int(feature_str[tile_start:tile_end])
                    
                    # Create a properties dictionary
                    properties = {
                        'GEOID': geoid,
                        'obsolescence_score': score,
                        'confidence': confidence,
                        'tile_count': tile_count,
                        'data_source': 'real'
                    }
                    
                    geoid_to_properties[geoid] = properties
                except Exception as e:
                    logger.warning(f"Could not extract properties from feature {i}: {e}")
            except Exception as e:
                logger.warning(f"Error processing feature {i}: {e}")
        
        logger.info(f"Extracted properties for {len(geoid_to_properties)} counties")
        return geoid_to_properties
    
    except Exception as e:
        logger.error(f"Error extracting features: {e}")
        return {}

def recreate_geojson(shapefile, properties_dict, output_file):
    """
    Recreate a GeoJSON file from the county shapefile and add properties from the dictionary.
    
    Args:
        shapefile: Path to the county shapefile
        properties_dict: Dictionary mapping GEOID to properties
        output_file: Path to save the recreated GeoJSON file
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Recreating GeoJSON file from {shapefile}")
    
    try:
        # Load the county shapefile
        counties = gpd.read_file(shapefile)
        logger.info(f"Loaded {len(counties)} counties from shapefile")
        
        # Filter to only include counties with properties
        counties_with_data = counties[counties['GEOID'].isin(properties_dict.keys())].copy()
        logger.info(f"Found {len(counties_with_data)} counties with data")
        
        # Add the properties to the GeoDataFrame
        for prop in ['obsolescence_score', 'confidence', 'tile_count', 'data_source']:
            counties_with_data[prop] = counties_with_data['GEOID'].apply(
                lambda geoid: properties_dict[geoid].get(prop, None)
            )
        
        # Save to GeoJSON
        counties_with_data.to_file(output_file, driver='GeoJSON')
        logger.info(f"Saved {len(counties_with_data)} counties to {output_file}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error recreating GeoJSON file: {e}")
        return False

def main():
    """Main function to recreate a GeoJSON file."""
    if len(sys.argv) < 3:
        print("Usage: python recreate_geojson.py <corrupted_geojson> <output_file>")
        sys.exit(1)
    
    corrupted_file = sys.argv[1]
    output_file = sys.argv[2]
    shapefile = 'data/tl_2024_us_county/tl_2024_us_county.shp'
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Extract valid features from the corrupted file
    properties_dict = extract_valid_features(corrupted_file)
    
    if not properties_dict:
        logger.error("Failed to extract any valid features")
        sys.exit(1)
    
    # Recreate the GeoJSON file
    if recreate_geojson(shapefile, properties_dict, output_file):
        logger.info(f"Successfully recreated GeoJSON file: {output_file}")
        sys.exit(0)
    else:
        logger.error(f"Failed to recreate GeoJSON file: {output_file}")
        sys.exit(1)

if __name__ == "__main__":
    main()
