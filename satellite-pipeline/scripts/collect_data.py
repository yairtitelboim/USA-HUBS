#!/usr/bin/env python3
"""
Satellite Data Collection Script

This script handles the collection of satellite data for counties
and processes it to calculate metrics.

Usage:
    python collect_data.py [options]

Options:
    --counties COUNTY_LIST    Comma-separated list of county FIPS codes
    --all-counties            Process all counties in the shapefile
    --state STATE_FIPS        Process all counties in a state
    --interval {daily,weekly,monthly}  Collection interval (for timestamping)
    --start-date START_DATE   Start date for satellite imagery (YYYY-MM-DD)
    --end-date END_DATE       End date for satellite imagery (YYYY-MM-DD)
    --credentials CRED_FILE   Path to GEE credentials JSON file
    --test                    Run in test mode with a small set of counties
"""

import os
import sys
import json
import logging
import argparse
import datetime
from pathlib import Path
from typing import List, Dict, Optional

import geopandas as gpd
import pandas as pd

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parents[1]))

# Import our modules
from src.collectors.gee_collector import GEECollector
from src.processors.metrics_processor import MetricsProcessor
from src.utils.time_series import TimeSeriesStore

# Configure logging
log_dir = Path(__file__).parents[1] / 'logs'
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'collection.log')
    ]
)
logger = logging.getLogger('collect_data')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Satellite Data Collection Script")
    
    # County selection options
    county_group = parser.add_mutually_exclusive_group(required=False)
    county_group.add_argument('--counties', help='Comma-separated list of county FIPS codes')
    county_group.add_argument('--all-counties', action='store_true', help='Process all counties in the shapefile')
    county_group.add_argument('--state', help='Process all counties in a state (state FIPS code)')
    county_group.add_argument('--test', action='store_true', help='Run in test mode with a small set of counties')
    
    # Date options
    parser.add_argument('--start-date', help='Start date for satellite imagery (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for satellite imagery (YYYY-MM-DD)')
    
    # Interval option
    parser.add_argument('--interval', choices=['daily', 'weekly', 'monthly'], 
                       default='weekly', help='Collection interval')
    
    # Credentials
    parser.add_argument('--credentials', help='Path to GEE credentials JSON file')
    
    # Processing options
    parser.add_argument('--skip-collection', action='store_true', 
                       help='Skip data collection and only process existing data')
    parser.add_argument('--skip-processing', action='store_true',
                       help='Skip processing collected data')
    
    return parser.parse_args()

def get_county_list(args, county_shapefile='../data/tl_2024_us_county/tl_2024_us_county.shp') -> List[str]:
    """
    Get the list of counties to process based on command line arguments.
    
    Args:
        args: Command line arguments
        county_shapefile: Path to the county shapefile
        
    Returns:
        List of county FIPS codes
    """
    try:
        # Load the county shapefile
        counties_gdf = gpd.read_file(county_shapefile)
        
        if args.counties:
            # Use the provided list of counties
            return [c.strip() for c in args.counties.split(',')]
            
        elif args.state:
            # Get all counties in a state
            state_counties = counties_gdf[counties_gdf['STATEFP'] == args.state]
            return state_counties['GEOID'].tolist()
            
        elif args.test:
            # Use a small test set (5 random counties)
            return counties_gdf.sample(5)['GEOID'].tolist()
            
        elif args.all_counties:
            # Use all counties
            return counties_gdf['GEOID'].tolist()
            
        else:
            # Default to a small test set
            logger.warning("No county selection option provided, using test mode")
            return counties_gdf.sample(3)['GEOID'].tolist()
            
    except Exception as e:
        logger.error(f"Error getting county list: {e}")
        # Return a default test set
        return ['06037', '36061', '17031']  # Los Angeles, New York, Cook (Chicago)

def get_date_range(args) -> tuple:
    """
    Get the date range for satellite imagery.
    
    Args:
        args: Command line arguments
        
    Returns:
        Tuple of (start_date, end_date) as strings
    """
    # Get current date
    today = datetime.date.today()
    
    # Default end date is today
    end_date = args.end_date or today.isoformat()
    
    # Default start date depends on the interval
    if not args.start_date:
        if args.interval == 'daily':
            # Use yesterday
            start_date = (today - datetime.timedelta(days=1)).isoformat()
        elif args.interval == 'weekly':
            # Use 7 days ago
            start_date = (today - datetime.timedelta(days=7)).isoformat()
        elif args.interval == 'monthly':
            # Use 30 days ago
            start_date = (today - datetime.timedelta(days=30)).isoformat()
        else:
            # Default to 7 days
            start_date = (today - datetime.timedelta(days=7)).isoformat()
    else:
        start_date = args.start_date
    
    return start_date, end_date

def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_args()
    
    # Get list of counties to process
    county_list = get_county_list(args)
    logger.info(f"Processing {len(county_list)} counties: {', '.join(county_list[:5])}" + 
               (f"... and {len(county_list)-5} more" if len(county_list) > 5 else ""))
    
    # Get date range
    start_date, end_date = get_date_range(args)
    logger.info(f"Date range: {start_date} to {end_date}")
    
    # Initialize components
    collector = GEECollector(credentials_path=args.credentials)
    processor = MetricsProcessor()
    ts_store = TimeSeriesStore()
    
    # Collect data if not skipped
    sample_files = []
    if not args.skip_collection:
        logger.info("Starting data collection...")
        
        for county_fips in county_list:
            try:
                logger.info(f"Collecting data for county {county_fips}")
                sample_file = collector.collect_county_data(
                    county_fips=county_fips,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if sample_file:
                    sample_files.append(sample_file)
                    logger.info(f"Successfully collected data for county {county_fips}")
                else:
                    logger.warning(f"No data collected for county {county_fips}")
            except Exception as e:
                logger.error(f"Error collecting data for county {county_fips}: {e}")
    else:
        logger.info("Skipping data collection as requested")
    
    # Process data if not skipped
    if not args.skip_processing:
        logger.info("Starting data processing...")
        
        for sample_file in sample_files:
            try:
                logger.info(f"Processing data from {sample_file}")
                results = processor.process_county_data(sample_file)
                
                if results:
                    # Add to time series store
                    county_fips = results.get("county_fips")
                    collection_date = results.get("collection_date")
                    metrics = results.get("metrics", {})
                    metadata = results.get("metadata", {})
                    
                    ts_store.add_data_point(
                        county_fips=county_fips,
                        timestamp=collection_date,
                        metrics=metrics,
                        metadata=metadata
                    )
                    
                    logger.info(f"Successfully processed data for county {county_fips}")
                else:
                    logger.warning(f"No results from processing {sample_file}")
            except Exception as e:
                logger.error(f"Error processing data from {sample_file}: {e}")
    else:
        logger.info("Skipping data processing as requested")
    
    logger.info("Collection run completed")

if __name__ == "__main__":
    main() 