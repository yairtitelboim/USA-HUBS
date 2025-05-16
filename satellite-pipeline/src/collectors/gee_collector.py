#!/usr/bin/env python3
"""
GEE Satellite Data Collector

This module handles collecting satellite imagery data from Google Earth Engine.
It provides functionality to fetch data for multiple counties and time periods.
"""

import os
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import ee
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parents[2] / 'logs' / 'collector.log')
    ]
)
logger = logging.getLogger('gee_collector')

# Constants from the original project
DEFAULT_BUCKET = "loghub-sentinel2-exports"
DEFAULT_PROJECT = "gentle-cinema-458613-f3"
DEFAULT_BANDS = ["B4", "B3", "B2"]
DEFAULT_SCALE = 10
DEFAULT_CRS = "EPSG:3857"
DEFAULT_MAX_PIXELS = 1e10

class GEECollector:
    """Google Earth Engine data collector for satellite imagery."""
    
    def __init__(self, 
                 credentials_path: Optional[str] = None,
                 county_shapefile: Optional[str] = None):
        """
        Initialize the GEE collector.
        
        Args:
            credentials_path: Path to GEE credentials JSON file
            county_shapefile: Path to county shapefile (default uses built-in)
        """
        self.credentials_path = credentials_path
        self.county_shapefile = county_shapefile or "../data/tl_2024_us_county/tl_2024_us_county.shp"
        self.initialized = False
        
        # Create necessary directories
        os.makedirs(Path(__file__).parents[2] / 'logs', exist_ok=True)
        os.makedirs(Path(__file__).parents[2] / 'data' / 'raw', exist_ok=True)
        
        # Try to initialize EE
        self._initialize_ee()
        
    def _initialize_ee(self) -> bool:
        """
        Initialize Earth Engine with service account credentials.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        logger.info("Initializing Earth Engine...")

        try:
            if self.credentials_path:
                # Check if the service account key file exists
                if not os.path.exists(self.credentials_path):
                    logger.error(f"Service account key file not found: {self.credentials_path}")
                    logger.info("Trying to initialize with default credentials...")
                    ee.Initialize()
                    logger.info("Earth Engine initialized with default credentials!")
                    self.initialized = True
                    return True

                # Initialize with service account credentials
                credentials = ee.ServiceAccountCredentials(None, self.credentials_path)
                ee.Initialize(credentials)
            else:
                # Try using the default credentials
                ee.Initialize()

            # Test the connection by making a simple request
            _ = ee.Image(1).getInfo()

            logger.info("Earth Engine initialized successfully!")
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Error initializing Earth Engine: {e}")
            logger.error("Please make sure your Google Earth Engine credentials are properly set up.")
            logger.error("You can authenticate using the earthengine command line tool:")
            logger.error("  earthengine authenticate")
            self.initialized = False
            return False
            
    def _mask_s2_clouds(self, img):
        """
        Mask clouds in Sentinel-2 imagery, using the same approach as in process_real_satellite_data.py.
        
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
        
    def _add_indices(self, img):
        """
        Add various indices to the satellite image.
        
        Args:
            img: Earth Engine image
            
        Returns:
            Earth Engine image with added indices
        """
        # Calculate NDVI (vegetation index)
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        # Calculate NDBI (built-up index)
        ndbi = img.normalizedDifference(['B11', 'B8']).rename('NDBI')
        
        # Calculate NDWI (water index)
        ndwi = img.normalizedDifference(['B3', 'B8']).rename('NDWI')
        
        # Calculate Modified Normalized Difference Water Index (MNDWI)
        mndwi = img.normalizedDifference(['B3', 'B11']).rename('MNDWI')
        
        # Calculate Urban Index (UI)
        ui = img.normalizedDifference(['B11', 'B7']).rename('UI')
        
        # Calculate Normalized Difference Moisture Index (NDMI)
        ndmi = img.normalizedDifference(['B8', 'B11']).rename('NDMI')
        
        # Add all indices to the image
        return img.addBands([ndvi, ndbi, ndwi, mndwi, ui, ndmi])
        
    def collect_county_data(self, 
                           county_fips: str,
                           start_date: str,
                           end_date: str,
                           output_dir: Optional[str] = None) -> str:
        """
        Collect satellite data for a specific county and time period.
        
        Args:
            county_fips: FIPS code of the county
            start_date: Start date for imagery collection (YYYY-MM-DD)
            end_date: End date for imagery collection (YYYY-MM-DD)
            output_dir: Directory to save the output data
            
        Returns:
            Path to the saved data file
        """
        if not self.initialized:
            if not self._initialize_ee():
                logger.error("Earth Engine not initialized. Cannot collect data.")
                return None
        
        logger.info(f"Collecting data for county {county_fips} from {start_date} to {end_date}")
        
        # Default output directory
        if output_dir is None:
            output_dir = str(Path(__file__).parents[2] / 'data' / 'raw')
            
        # Create timestamp-based subdirectory
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        county_dir = os.path.join(output_dir, f"{county_fips}_{timestamp}")
        os.makedirs(county_dir, exist_ok=True)
        
        try:
            # Load county shapefile
            counties_gdf = gpd.read_file(self.county_shapefile)
            county_data = counties_gdf[counties_gdf['GEOID'] == county_fips]
            
            if len(county_data) == 0:
                logger.error(f"County with FIPS code {county_fips} not found in shapefile")
                return None
                
            # Convert to GEE geometry
            county_geometry = ee.Geometry(json.loads(county_data.geometry.iloc[0].to_json()))
            
            # Simplify the geometry to reduce complexity (as in process_real_satellite_data.py)
            simplified_geometry = county_geometry.simplify(maxError=100)
            
            # Get the centroid of the county to reduce memory usage (as in process_real_satellite_data.py)
            centroid = simplified_geometry.centroid()
            
            # Create a buffer around the centroid (10km radius) - this reduces computation time
            # while still getting representative data
            buffer = centroid.buffer(10000)
            
            # Use the buffer instead of the full county geometry
            sample_geometry = buffer
            
            # Get Sentinel-2 imagery
            s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                            .filterBounds(sample_geometry)
                            .filterDate(start_date, end_date)
                            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                            .limit(10))  # Limit to 10 images to reduce computation time
            
            # Check if we have any images
            image_count = s2_collection.size().getInfo()
            logger.info(f"Found {image_count} Sentinel-2 images for county {county_fips}")
            
            if image_count == 0:
                logger.warning(f"No suitable Sentinel-2 images found for county {county_fips}")
                return None
                
            # Apply cloud masking and add indices
            s2_processed = s2_collection.map(self._mask_s2_clouds).map(self._add_indices)
            
            # Compute a median composite
            median_image = s2_processed.median()
            
            # Add timestamp information
            metadata_file = os.path.join(county_dir, "metadata.json")
            metadata = {
                "county_fips": county_fips,
                "county_name": county_data.iloc[0]['NAME'],
                "state_fips": county_data.iloc[0]['STATEFP'],
                "start_date": start_date,
                "end_date": end_date,
                "collection_timestamp": timestamp,
                "image_count": image_count
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            # Get the band values for key indices
            bands_of_interest = ['NDVI', 'NDBI', 'UI', 'NDWI', 'MNDWI', 'NDMI']
            
            # Sample points across the county 
            points = simplified_geometry.sample(
                numPoints=500,  # Sample 500 points to get good coverage
                seed=42,        # Fixed seed for reproducibility
                dropNulls=True,
                geometries=True
            )
            
            # Extract values at these points
            samples = median_image.select(bands_of_interest).sampleRegions(
                collection=points,
                scale=20,  # 20m resolution
                geometries=True
            )
            
            # Download the samples
            samples_data = samples.getInfo()
            
            # Save to GeoJSON
            output_file = os.path.join(county_dir, f"{county_fips}_samples.geojson")
            
            with open(output_file, 'w') as f:
                json.dump(samples_data, f, indent=2)
                
            logger.info(f"Successfully collected data for county {county_fips}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error collecting data for county {county_fips}: {e}")
            return None
            
    def collect_bulk(self,
                    county_list: List[str],
                    start_date: str,
                    end_date: str,
                    output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Collect data for multiple counties.
        
        Args:
            county_list: List of county FIPS codes
            start_date: Start date for imagery collection (YYYY-MM-DD)
            end_date: End date for imagery collection (YYYY-MM-DD)
            output_dir: Directory to save the output data
            
        Returns:
            Dictionary mapping county FIPS codes to output file paths
        """
        results = {}
        
        for county_fips in county_list:
            output_file = self.collect_county_data(
                county_fips=county_fips,
                start_date=start_date,
                end_date=end_date,
                output_dir=output_dir
            )
            
            results[county_fips] = output_file
            
        return results


if __name__ == "__main__":
    # Simple test run
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect satellite data for counties")
    parser.add_argument('--county', required=True, help='County FIPS code')
    parser.add_argument('--start-date', default='2023-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2023-12-31', help='End date (YYYY-MM-DD)')
    parser.add_argument('--credentials', help='Path to GEE credentials JSON file')
    args = parser.parse_args()
    
    collector = GEECollector(credentials_path=args.credentials)
    
    output_file = collector.collect_county_data(
        county_fips=args.county,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    if output_file:
        print(f"Data collected successfully: {output_file}")
    else:
        print("Data collection failed.") 