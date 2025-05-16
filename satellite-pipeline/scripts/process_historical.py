#!/usr/bin/env python3
"""
Historical Satellite Data Processing Script

This script processes historical satellite data for counties over a specific time range,
using a date-by-date approach with configurable intervals.

Usage:
    python process_historical.py [options]

Options:
    --counties COUNTY_LIST    Comma-separated list of county FIPS codes
    --all-counties            Process all counties in the shapefile
    --state STATE_FIPS        Process all counties in a state
    --start-date START_DATE   Start date for satellite imagery (YYYY-MM-DD)
    --end-date END_DATE       End date for satellite imagery (YYYY-MM-DD)
    --interval {monthly,quarterly,yearly}  Time interval for processing
    --credentials CRED_FILE   Path to GEE credentials JSON file
    --parallel N              Number of parallel processes to use
"""

import os
import sys
import time
import json
import yaml
import logging
import argparse
import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dateutil.relativedelta import relativedelta
import concurrent.futures

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
        logging.FileHandler(log_dir / 'historical_processing.log')
    ]
)
logger = logging.getLogger('process_historical')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Historical Satellite Data Processing Script")
    
    # County selection options
    county_group = parser.add_mutually_exclusive_group(required=False)
    county_group.add_argument('--counties', help='Comma-separated list of county FIPS codes')
    county_group.add_argument('--all-counties', action='store_true', help='Process all counties in the shapefile')
    county_group.add_argument('--state', help='Process all counties in a state (state FIPS code)')
    
    # Date options
    parser.add_argument('--start-date', required=True, help='Start date for satellite imagery (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date for satellite imagery (YYYY-MM-DD)')
    
    # Interval option
    parser.add_argument('--interval', choices=['monthly', 'quarterly', 'yearly'], 
                       default='quarterly', help='Time interval for processing')
    
    # Credentials
    parser.add_argument('--credentials', help='Path to GEE credentials JSON file')
    
    # Parallel processing
    parser.add_argument('--parallel', type=int, default=1, 
                       help='Number of parallel processes to use')
    
    return parser.parse_args()

def load_settings():
    """Load settings from configuration file."""
    settings_path = Path(__file__).parents[1] / 'config' / 'settings.yaml'
    with open(settings_path, 'r') as f:
        return yaml.safe_load(f)

def get_county_list(args, county_shapefile=None) -> List[str]:
    """
    Get the list of counties to process based on command line arguments.
    
    Args:
        args: Command line arguments
        county_shapefile: Path to the county shapefile
        
    Returns:
        List of county FIPS codes
    """
    try:
        # Default shapefile path
        if county_shapefile is None:
            county_shapefile = str(Path(__file__).parents[1] / 'data' / 'tl_2024_us_county' / 'tl_2024_us_county.shp')
        
        # Load the county shapefile
        counties_gdf = gpd.read_file(county_shapefile)
        
        if args.counties:
            # Use the provided list of counties
            return [c.strip() for c in args.counties.split(',')]
            
        elif args.state:
            # Get all counties in a state
            state_counties = counties_gdf[counties_gdf['STATEFP'] == args.state]
            return state_counties['GEOID'].tolist()
            
        elif args.all_counties:
            # Use all counties
            return counties_gdf['GEOID'].tolist()
            
        else:
            # Default to a small test set
            logger.warning("No county selection option provided, using test mode with 3 counties")
            return counties_gdf.sample(3)['GEOID'].tolist()
            
    except Exception as e:
        logger.error(f"Error getting county list: {e}")
        # Return a default test set
        return ['06037', '36061', '17031']  # Los Angeles, New York, Cook (Chicago)

def generate_time_intervals(start_date_str, end_date_str, interval):
    """
    Generate time intervals based on the specified interval type.
    
    Args:
        start_date_str: Start date as string (YYYY-MM-DD)
        end_date_str: End date as string (YYYY-MM-DD)
        interval: Interval type (monthly, quarterly, yearly)
        
    Returns:
        List of (start_date, end_date) tuples for each interval
    """
    # Parse dates
    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    intervals = []
    current_start = start_date
    
    # Generate intervals based on specified type
    while current_start <= end_date:
        if interval == 'monthly':
            current_end = current_start + relativedelta(months=1, days=-1)
        elif interval == 'quarterly':
            current_end = current_start + relativedelta(months=3, days=-1)
        elif interval == 'yearly':
            current_end = current_start + relativedelta(years=1, days=-1)
        else:
            # Default to quarterly
            current_end = current_start + relativedelta(months=3, days=-1)
        
        # Ensure end date doesn't exceed the overall end date
        current_end = min(current_end, end_date)
        
        intervals.append((current_start.isoformat(), current_end.isoformat()))
        
        # Move to next interval
        if interval == 'monthly':
            current_start = current_start + relativedelta(months=1)
        elif interval == 'quarterly':
            current_start = current_start + relativedelta(months=3)
        elif interval == 'yearly':
            current_start = current_start + relativedelta(years=1)
        else:
            # Default to quarterly
            current_start = current_start + relativedelta(months=3)
    
    return intervals

def process_county_interval(county_fips, start_date, end_date, credentials_path):
    """
    Process a single county for a specific time interval.
    
    Args:
        county_fips: County FIPS code
        start_date: Start date for satellite imagery (YYYY-MM-DD)
        end_date: End date for satellite imagery (YYYY-MM-DD)
        credentials_path: Path to GEE credentials JSON file
        
    Returns:
        Dictionary with result information
    """
    logger.info(f"Processing county {county_fips} for {start_date} to {end_date}")
    
    try:
        # Initialize components
        collector = GEECollector(credentials_path=credentials_path)
        processor = MetricsProcessor()
        ts_store = TimeSeriesStore()
        
        # Collect satellite data
        sample_file = collector.collect_county_data(
            county_fips=county_fips,
            start_date=start_date,
            end_date=end_date
        )
        
        if not sample_file:
            logger.warning(f"No data collected for county {county_fips} during {start_date} to {end_date}")
            return {
                "county_fips": county_fips,
                "start_date": start_date,
                "end_date": end_date,
                "status": "no_data",
                "error": None
            }
        
        # Process the data
        results = processor.process_county_data(sample_file)
        
        if not results:
            logger.warning(f"Processing failed for county {county_fips} during {start_date} to {end_date}")
            return {
                "county_fips": county_fips,
                "start_date": start_date,
                "end_date": end_date,
                "status": "processing_failed",
                "error": None
            }
        
        # Store in time series
        county_fips = results.get("county_fips")
        collection_date = results.get("collection_date")
        metrics = results.get("metrics", {})
        metadata = results.get("metadata", {})
        
        # Override the timestamp with the middle of the interval for better time representation
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        mid_dt = start_dt + (end_dt - start_dt) / 2
        timestamp = mid_dt.isoformat()
        
        # Add to time series store
        success = ts_store.add_data_point(
            county_fips=county_fips,
            timestamp=timestamp,
            metrics=metrics,
            metadata=metadata
        )
        
        if not success:
            logger.warning(f"Failed to add data point to time series for county {county_fips}")
            return {
                "county_fips": county_fips,
                "start_date": start_date,
                "end_date": end_date,
                "status": "storage_failed",
                "error": None
            }
        
        logger.info(f"Successfully processed county {county_fips} for {start_date} to {end_date}")
        return {
            "county_fips": county_fips,
            "start_date": start_date,
            "end_date": end_date,
            "status": "success",
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Error processing county {county_fips} for {start_date} to {end_date}: {e}")
        return {
            "county_fips": county_fips,
            "start_date": start_date,
            "end_date": end_date,
            "status": "error",
            "error": str(e)
        }

def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_args()
    
    # Load settings
    settings = load_settings()
    
    # Get list of counties to process
    county_list = get_county_list(args)
    logger.info(f"Processing {len(county_list)} counties: {', '.join(county_list[:5])}" + 
               (f"... and {len(county_list)-5} more" if len(county_list) > 5 else ""))
    
    # Generate time intervals
    intervals = generate_time_intervals(args.start_date, args.end_date, args.interval)
    logger.info(f"Processing {len(intervals)} time intervals from {args.start_date} to {args.end_date}")
    
    # Create a list of all tasks (county + interval combinations)
    tasks = []
    for county_fips in county_list:
        for start_date, end_date in intervals:
            tasks.append((county_fips, start_date, end_date))
    
    logger.info(f"Total tasks to process: {len(tasks)}")
    
    # Process tasks in parallel if requested
    start_time = time.time()
    
    if args.parallel > 1:
        logger.info(f"Using {args.parallel} parallel processes")
        results = []
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.parallel) as executor:
            futures = {}
            
            for county_fips, start_date, end_date in tasks:
                future = executor.submit(
                    process_county_interval,
                    county_fips,
                    start_date,
                    end_date,
                    args.credentials
                )
                futures[future] = (county_fips, start_date, end_date)
            
            for future in concurrent.futures.as_completed(futures):
                county_fips, start_date, end_date = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Completed task for county {county_fips} ({start_date} to {end_date})")
                except Exception as e:
                    logger.error(f"Task failed for county {county_fips} ({start_date} to {end_date}): {e}")
    else:
        # Process tasks sequentially
        logger.info("Processing tasks sequentially")
        results = []
        
        for county_fips, start_date, end_date in tasks:
            result = process_county_interval(
                county_fips,
                start_date,
                end_date,
                args.credentials
            )
            results.append(result)
    
    # Calculate statistics
    success_count = sum(1 for r in results if r["status"] == "success")
    no_data_count = sum(1 for r in results if r["status"] == "no_data")
    error_count = sum(1 for r in results if r["status"] in ["error", "processing_failed", "storage_failed"])
    
    elapsed_time = time.time() - start_time
    
    logger.info(f"Historical processing completed in {elapsed_time:.1f} seconds")
    logger.info(f"Results: {success_count} successful, {no_data_count} no data, {error_count} errors")
    
    # Save summary to file
    summary_file = Path(__file__).parents[1] / 'logs' / f"historical_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    summary = {
        "start_date": args.start_date,
        "end_date": args.end_date,
        "interval": args.interval,
        "counties": county_list,
        "total_tasks": len(tasks),
        "success_count": success_count,
        "no_data_count": no_data_count,
        "error_count": error_count,
        "elapsed_time": elapsed_time,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Summary saved to {summary_file}")

if __name__ == "__main__":
    main() 