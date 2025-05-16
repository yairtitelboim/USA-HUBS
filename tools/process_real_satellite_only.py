#!/usr/bin/env python3
"""
Process Real Satellite Data Only

This script processes real satellite data for counties with no fallback to simulated data.
It processes one county at a time to avoid memory issues and provides detailed logging.

Usage:
    python process_real_satellite_only.py [--county COUNTY_FIPS] [--output OUTPUT_FILE]

Options:
    --county COUNTY_FIPS   FIPS code of the county to process [required]
    --output OUTPUT_FILE   Path to save the updated county scores [default: data/final/real_county_scores.geojson]
    --service-account-key  Path to Google Earth Engine service account key [default: config/gee/gentle-cinema-458613-f3-51d8ea2711e7.json]
"""

import os
import argparse
import geopandas as gpd
import pandas as pd
import numpy as np
import subprocess
import time
import datetime
import ee
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/satellite_processing.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process Real Satellite Data Only')
    parser.add_argument('--county', required=True,
                        help='FIPS code of the county to process')
    parser.add_argument('--output', default='data/final/real_county_scores.geojson',
                        help='Path to save the updated county scores')
    parser.add_argument('--service-account-key',
                        default='config/gee/gentle-cinema-458613-f3-51d8ea2711e7.json',
                        help='Path to Google Earth Engine service account key')
    parser.add_argument('--start-date', default='2023-01-01',
                        help='Start date for satellite imagery (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2023-12-31',
                        help='End date for satellite imagery (YYYY-MM-DD)')
    return parser.parse_args()

def initialize_earth_engine(service_account_key):
    """
    Initialize Earth Engine with service account credentials.

    Args:
        service_account_key: Path to the service account key file

    Returns:
        True if initialization was successful, False otherwise
    """
    logger.info("Initializing Earth Engine...")

    try:
        # Check if the service account key file exists
        if not os.path.exists(service_account_key):
            logger.error(f"Service account key file not found: {service_account_key}")
            return False

        # Initialize with service account credentials
        credentials = ee.ServiceAccountCredentials(None, service_account_key)
        ee.Initialize(credentials)

        # Test the connection by making a simple request
        _ = ee.Image(1).getInfo()

        logger.info("Earth Engine initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"Error initializing Earth Engine: {e}")
        return False

def mask_s2_clouds(img):
    """
    Mask clouds in Sentinel-2 imagery.

    Args:
        img: Earth Engine image

    Returns:
        Earth Engine image with clouds masked
    """
    # Use the cloud probability band (MSK_CLDPRB) and cloud classification bands
    cloudProb = img.select('MSK_CLDPRB')
    cloudOpaque = img.select('MSK_CLASSI_OPAQUE')
    cloudCirrus = img.select('MSK_CLASSI_CIRRUS')

    # Create a combined mask (cloud probability < 50% AND not classified as opaque or cirrus cloud)
    mask = cloudProb.lt(50).And(cloudOpaque.eq(0)).And(cloudCirrus.eq(0))

    # Apply the mask and scale the pixel values
    return img.updateMask(mask).divide(10000)

def get_county_data(county_fips):
    """
    Get county data from the shapefile.

    Args:
        county_fips: FIPS code of the county

    Returns:
        County data as a GeoDataFrame row, or None if not found
    """
    logger.info(f"Getting data for county FIPS: {county_fips}")

    try:
        # Load the county shapefile
        shapefile_path = 'data/tl_2024_us_county/tl_2024_us_county.shp'
        counties_gdf = gpd.read_file(shapefile_path)

        # Filter for the specified county
        county_data = counties_gdf[counties_gdf['GEOID'] == county_fips]

        if len(county_data) == 0:
            logger.error(f"County with FIPS code {county_fips} not found in shapefile")
            return None

        logger.info(f"Found county: {county_data.iloc[0]['NAME']}, {county_data.iloc[0]['STATEFP']}")
        return county_data.iloc[0]

    except Exception as e:
        logger.error(f"Error getting county data: {e}")
        return None

def calculate_obsolescence_score(county_geometry, start_date, end_date):
    """
    Calculate obsolescence score for a county using real satellite data.
    No fallbacks to simulated data - only real satellite data is used.

    Args:
        county_geometry: County geometry as a GeoJSON-like object
        start_date: Start date for satellite imagery
        end_date: End date for satellite imagery

    Returns:
        Tuple of (obsolescence_score, confidence, tile_count) or None if calculation fails
    """
    logger.info("Calculating obsolescence score using real satellite data...")

    try:
        # Convert county geometry to Earth Engine geometry
        ee_geometry = ee.Geometry(county_geometry)

        # Simplify the geometry to reduce complexity but preserve shape
        logger.info("Simplifying county geometry...")
        simplified_geometry = ee_geometry.simplify(maxError=50)

        # Use a smaller sample area to avoid memory issues
        # Instead of just the centroid, use a more representative sample
        logger.info("Creating sample area...")

        # Get the bounds of the county
        bounds = simplified_geometry.bounds()

        # Create a grid of 4 points within the bounds to sample from different parts of the county
        coords = bounds.coordinates().get(0).getInfo()
        minx, miny = coords[0]
        maxx, maxy = coords[2]

        # Calculate center and quarter points
        centerx = (minx + maxx) / 2
        centery = (miny + maxy) / 2

        # Create 4 sample points
        sample_points = [
            ee.Geometry.Point([centerx, centery]),  # Center
            ee.Geometry.Point([minx + (maxx - minx) * 0.25, miny + (maxy - miny) * 0.25]),  # Bottom-left quarter
            ee.Geometry.Point([minx + (maxx - minx) * 0.25, miny + (maxy - miny) * 0.75]),  # Top-left quarter
            ee.Geometry.Point([minx + (maxx - minx) * 0.75, miny + (maxy - miny) * 0.75])   # Top-right quarter
        ]

        # Create small buffers around each point (1km radius)
        sample_areas = [point.buffer(1000) for point in sample_points]

        # Combine the sample areas
        sample_geometry = ee.Geometry.MultiPolygon([area.coordinates() for area in sample_areas])

        logger.info("Fetching Sentinel-2 imagery...")
        # Get Sentinel-2 imagery for the sample area with less cloud cover
        s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                         .filterBounds(sample_geometry)
                         .filterDate(start_date, end_date)
                         .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))  # Filter for less cloudy images
                         .sort('CLOUDY_PIXEL_PERCENTAGE')  # Sort by cloud cover
                         .limit(10)  # Get more images to ensure we have enough data
                         .map(mask_s2_clouds))

        # Get the number of images (tile count)
        tile_count = s2_collection.size().getInfo()
        logger.info(f"Found {tile_count} Sentinel-2 images")

        # If no images are available, return None - no fallback
        if tile_count == 0:
            logger.error("No Sentinel-2 images available for this area")
            return None

        logger.info("Calculating vegetation and built-up indices...")
        # Calculate multiple indices to better characterize the area
        def add_indices(img):
            # NDVI - vegetation index
            ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI')

            # NDBI - built-up index
            ndbi = img.normalizedDifference(['B11', 'B8']).rename('NDBI')

            # NDWI - water index
            ndwi = img.normalizedDifference(['B3', 'B8']).rename('NDWI')

            # BSI - bare soil index
            bsi_numerator = (img.select('B11').add(img.select('B4'))).subtract(img.select('B8').add(img.select('B2')))
            bsi_denominator = (img.select('B11').add(img.select('B4'))).add(img.select('B8').add(img.select('B2')))
            bsi = bsi_numerator.divide(bsi_denominator).rename('BSI')

            return img.addBands([ndvi, ndbi, ndwi, bsi])

        s2_with_indices = s2_collection.map(add_indices)

        # Calculate median values to reduce noise
        logger.info("Calculating median values...")
        median_img = s2_with_indices.median()

        # Calculate individual indices for the sample area
        logger.info("Calculating individual indices...")

        # Use a direct approach with real Landsat 8 satellite imagery from NASA/USGS
        logger.info("Accessing real Landsat 8 satellite imagery from NASA/USGS...")

        # Get a single Landsat 8 image for the area (more reliable than Sentinel-2 for this purpose)
        landsat = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                  .filterBounds(simplified_geometry)
                  .filterDate(start_date, end_date)
                  .sort('CLOUD_COVER')
                  .first())

        if landsat is None:
            logger.error("No Landsat 8 imagery available for this area")
            return None

        # Scale the surface reflectance bands
        landsat = landsat.select(['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7']).multiply(0.0000275).add(-0.2)

        # Calculate NDVI (vegetation index)
        ndvi = landsat.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')

        # Calculate NDBI (built-up index)
        ndbi = landsat.normalizedDifference(['SR_B6', 'SR_B5']).rename('NDBI')

        # Calculate BSI (bare soil index)
        bsi_num = landsat.select('SR_B6').add(landsat.select('SR_B4'))
        bsi_denom = landsat.select('SR_B5').add(landsat.select('SR_B2'))
        bsi = bsi_num.subtract(bsi_denom).divide(bsi_num.add(bsi_denom)).rename('BSI')

        # Add all indices to the image
        landsat_with_indices = landsat.addBands([ndvi, ndbi, bsi])

        # Use a smaller sample area (just the centroid with a buffer)
        county_centroid = simplified_geometry.centroid()
        sample_area = county_centroid.buffer(5000)

        # Calculate mean values for the indices
        try:
            logger.info("Calculating index values...")
            mean_values = landsat_with_indices.select(['NDVI', 'NDBI', 'BSI']).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=sample_area,
                scale=100,  # Use a larger scale to reduce computation
                maxPixels=1e8
            ).getInfo()

            logger.info(f"Mean values: {mean_values}")

            # Extract the values
            ndvi_value = mean_values.get('NDVI')
            ndbi_value = mean_values.get('NDBI')
            bsi_value = mean_values.get('BSI')

            # Check if we have valid values
            if ndvi_value is None or ndbi_value is None or bsi_value is None:
                logger.error("Missing index values from Landsat 8")

                # Try analyzing the entire county with real satellite data
                logger.info("Analyzing the entire county with real satellite data...")
                mean_values = landsat_with_indices.select(['NDVI', 'NDBI', 'BSI']).reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=simplified_geometry,
                    scale=500,  # Use an even larger scale
                    maxPixels=1e8
                ).getInfo()

                logger.info(f"Mean values (full county): {mean_values}")

                # Extract the values
                ndvi_value = mean_values.get('NDVI')
                ndbi_value = mean_values.get('NDBI')
                bsi_value = mean_values.get('BSI')

                if ndvi_value is None or ndbi_value is None or bsi_value is None:
                    logger.error("Still missing index values, cannot calculate obsolescence score")
                    return None

        except Exception as e:
            logger.error(f"Error calculating index values: {e}")
            return None

        # Log the raw values
        logger.info(f"Raw NDVI: {ndvi_value}")
        logger.info(f"Raw NDBI: {ndbi_value}")
        logger.info(f"Raw BSI: {bsi_value}")

        # Check if we have valid values
        if ndvi_value is None or ndbi_value is None or bsi_value is None:
            logger.error("Missing index values, cannot calculate obsolescence score")
            return None

        # Calculate obsolescence score directly
        # Formula: (NDBI + BSI - NDVI + 1) / 3
        # This gives a value between 0-1 where higher values indicate more obsolescence
        obsolescence_value = (ndbi_value + bsi_value - ndvi_value + 1) / 3

        # Calculate confidence based on the number of images
        confidence = min(0.95, 0.5 + (tile_count / 20))

        # Log the raw values and calculated obsolescence score
        raw_values = {
            'NDVI': ndvi_value,
            'NDBI': ndbi_value,
            'BSI': bsi_value,
            'Obsolescence': obsolescence_value
        }

        logger.info(f"Raw index values: {raw_values}")
        logger.info(f"Calculated obsolescence score: {obsolescence_value:.4f}")

        # Ensure the obsolescence score is valid
        if obsolescence_value is None:
            logger.error("Failed to calculate obsolescence score from satellite data")
            return None

        # Ensure the score is in the 0-1 range
        obsolescence_score = max(0, min(1, obsolescence_value))

        logger.info(f"Successfully calculated real obsolescence score: {obsolescence_score:.2f}")
        return (obsolescence_score, confidence, tile_count)

    except Exception as e:
        logger.error(f"Error calculating obsolescence score: {e}")
        return None

def update_county_scores(county_data, obsolescence_data, output_file):
    """
    Update county scores in the output file.
    Only real data is saved - no simulated or default values.

    Args:
        county_data: County data as a GeoDataFrame row
        obsolescence_data: Tuple of (obsolescence_score, confidence, tile_count)
        output_file: Path to the output file

    Returns:
        True if update was successful, False otherwise
    """
    logger.info(f"Updating county scores in {output_file}...")

    try:
        # Extract obsolescence data
        obsolescence_score, confidence, tile_count = obsolescence_data

        # Verify we have valid data
        if obsolescence_score is None:
            logger.error("Cannot update county scores with None obsolescence score")
            return False

        # Create a new GeoDataFrame with the county data
        county_gdf = gpd.GeoDataFrame([county_data], crs="EPSG:4326")

        # Add the obsolescence data
        county_gdf['obsolescence_score'] = float(obsolescence_score)  # Ensure it's a float
        county_gdf['confidence'] = float(confidence)  # Ensure it's a float
        county_gdf['tile_count'] = int(tile_count)  # Ensure it's an integer
        county_gdf['data_source'] = 'real'  # This is real satellite data
        county_gdf['processed_at'] = datetime.datetime.now().isoformat()

        # Load existing county scores if the file exists
        if os.path.exists(output_file):
            try:
                existing_gdf = gpd.read_file(output_file)
                logger.info(f"Loaded {len(existing_gdf)} counties from existing GeoJSON file")

                # Create a set of existing GEOIDs
                if 'GEOID' in existing_gdf.columns:
                    existing_geoids = set(existing_gdf['GEOID'].values)
                else:
                    existing_geoids = set()

                # Check if the county already exists in the dataset
                if county_data['GEOID'] in existing_geoids:
                    logger.info(f"County {county_data['GEOID']} already exists in the dataset, updating...")
                    # Remove the existing county
                    existing_gdf = existing_gdf[existing_gdf['GEOID'] != county_data['GEOID']]

                # Convert both dataframes to the same CRS if needed
                if existing_gdf.crs != county_gdf.crs:
                    logger.info(f"Converting CRS from {county_gdf.crs} to {existing_gdf.crs}")
                    county_gdf = county_gdf.to_crs(existing_gdf.crs)

                # Combine existing and new counties
                combined_gdf = pd.concat([existing_gdf, county_gdf], ignore_index=True)
            except Exception as e:
                logger.error(f"Error loading existing GeoJSON file: {e}")
                logger.info("Creating new GeoJSON file")
                combined_gdf = county_gdf
        else:
            logger.info("Output file does not exist, creating new GeoJSON file")
            combined_gdf = county_gdf

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Save the updated county scores
        combined_gdf.to_file(output_file, driver='GeoJSON')

        logger.info(f"Saved {len(combined_gdf)} counties to {output_file}")
        logger.info(f"Updated county {county_data['NAME']}, {county_data['STATEFP']} with obsolescence score: {obsolescence_score:.2f}")

        return True

    except Exception as e:
        logger.error(f"Error updating county scores: {e}")
        return False

def main():
    """
    Main function to process real satellite data for a county.
    Only processes and saves real data - no simulated or default values.
    """
    args = parse_args()

    logger.info(f"Processing county {args.county} using real satellite data only")
    logger.info(f"Date range: {args.start_date} to {args.end_date}")

    # Initialize Earth Engine
    if not initialize_earth_engine(args.service_account_key):
        logger.error("Failed to initialize Earth Engine. Exiting.")
        sys.exit(1)

    # Get county data
    county_data = get_county_data(args.county)
    if county_data is None:
        logger.error("Failed to get county data. Exiting.")
        sys.exit(1)

    logger.info(f"Processing county: {county_data['NAME']}, {county_data['STATEFP']} (FIPS: {args.county})")

    # Calculate obsolescence score using real satellite data
    obsolescence_data = calculate_obsolescence_score(
        county_data.geometry.__geo_interface__,
        args.start_date,
        args.end_date
    )

    # If we couldn't calculate a valid score, exit
    if obsolescence_data is None:
        logger.error("Failed to calculate real obsolescence score. No fallback to simulated data. Exiting.")
        sys.exit(1)

    # Update county scores with real data
    if not update_county_scores(county_data, obsolescence_data, args.output):
        logger.error("Failed to update county scores. Exiting.")
        sys.exit(1)

    logger.info(f"Successfully processed real satellite data for county {args.county}")
    logger.info(f"Obsolescence score: {obsolescence_data[0]:.2f}, Confidence: {obsolescence_data[1]:.2f}, Tile count: {obsolescence_data[2]}")

if __name__ == "__main__":
    main()
