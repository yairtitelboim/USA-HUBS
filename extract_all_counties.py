#!/usr/bin/env python3
"""
Extract all county data from the county_scores.geojson file and merge with shapefile.

This script:
1. Uses a more robust approach to extract all county data from county_scores.geojson
2. Merges this data with the county shapefile
3. Creates a new GeoJSON file with the actual county boundaries and the scores data
"""

import json
import geopandas as gpd
import pandas as pd
import os
import re
import logging
from shapely.geometry import shape
import csv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_county_data(geojson_path):
    """Extract county data from a potentially corrupted GeoJSON file."""
    county_data = []

    try:
        # First try to extract GEOID and scores using regex
        with open(geojson_path, 'r') as f:
            content = f.read()

        # Find all GEOIDs
        geoid_pattern = r'"GEOID"\s*:\s*"(\d+)"'
        geoids = re.findall(geoid_pattern, content)

        # Find all obsolescence scores
        obs_score_pattern = r'"obsolescence_score"\s*:\s*([\d\.]+)'
        obs_scores = re.findall(obs_score_pattern, content)

        # Find all growth potential scores
        growth_pattern = r'"growth_potential_score"\s*:\s*([\d\.]+)'
        growth_scores = re.findall(growth_pattern, content)

        # Find all confidence values
        confidence_pattern = r'"confidence"\s*:\s*([\d\.]+)'
        confidence_values = re.findall(confidence_pattern, content)

        # Find all tile counts
        tile_count_pattern = r'"tile_count"\s*:\s*(\d+)'
        tile_counts = re.findall(tile_count_pattern, content)

        # Find all county names
        name_pattern = r'"NAME"\s*:\s*"([^"]+)"'
        names = re.findall(name_pattern, content)

        # Find all state names
        state_pattern = r'"STATE"\s*:\s*"([^"]+)"'
        states = re.findall(state_pattern, content)

        # Make sure we have the same number of each
        min_length = min(len(geoids), len(obs_scores), len(growth_scores), len(confidence_values), len(tile_counts))

        logger.info(f"Found {len(geoids)} GEOIDs, {len(obs_scores)} obsolescence scores, {len(growth_scores)} growth scores")
        logger.info(f"Found {len(confidence_values)} confidence values, {len(tile_counts)} tile counts")
        logger.info(f"Found {len(names)} county names, {len(states)} state names")
        logger.info(f"Using minimum length: {min_length}")

        # Create a CSV file with the extracted data for debugging
        csv_path = os.path.join(os.path.dirname(geojson_path), 'extracted_county_data.csv')
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['GEOID', 'NAME', 'STATE', 'obsolescence_score', 'growth_potential_score', 'confidence', 'tile_count'])

            # Create county data objects
            for i in range(min_length):
                if i < len(geoids) and i < len(obs_scores) and i < len(growth_scores) and i < len(confidence_values) and i < len(tile_counts):
                    county = {
                        'GEOID': geoids[i],
                        'obsolescence_score': float(obs_scores[i]),
                        'growth_potential_score': float(growth_scores[i]) if i < len(growth_scores) else None,
                        'confidence': float(confidence_values[i]) if i < len(confidence_values) else None,
                        'tile_count': int(tile_counts[i]) if i < len(tile_counts) else None,
                    }

                    # Add name and state if available
                    if i < len(names):
                        county['NAME'] = names[i]
                    if i < len(states):
                        county['STATE'] = states[i]

                    county_data.append(county)

                    # Write to CSV
                    writer.writerow([
                        geoids[i],
                        names[i] if i < len(names) else '',
                        states[i] if i < len(states) else '',
                        obs_scores[i],
                        growth_scores[i] if i < len(growth_scores) else '',
                        confidence_values[i] if i < len(confidence_values) else '',
                        tile_counts[i] if i < len(tile_counts) else ''
                    ])

        logger.info(f"Extracted data for {len(county_data)} counties")
        logger.info(f"Saved extracted data to {csv_path}")
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
        for col in ['obsolescence_score', 'growth_potential_score', 'confidence', 'tile_count']:
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
                for col in ['obsolescence_score', 'growth_potential_score', 'confidence', 'tile_count']:
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
    county_scores_path = os.path.join(base_dir, 'data', 'final', 'comprehensive_county_scores.geojson')
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
