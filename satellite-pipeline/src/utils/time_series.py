#!/usr/bin/env python3
"""
Time Series Utilities

This module provides functions for storing and retrieving time series data
for county metrics.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parents[2] / 'logs' / 'time_series.log')
    ]
)
logger = logging.getLogger('time_series')

class TimeSeriesStore:
    """Store and retrieve time series data for county metrics."""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the time series store.
        
        Args:
            data_dir: Directory to store time series data
        """
        self.data_dir = data_dir or str(Path(__file__).parents[2] / 'data' / 'processed' / 'time_series')
        
        # Create necessary directories
        os.makedirs(self.data_dir, exist_ok=True)
        
    def get_county_file_path(self, county_fips: str) -> str:
        """
        Get the file path for a county's time series data.
        
        Args:
            county_fips: County FIPS code
            
        Returns:
            Path to the county's time series file
        """
        return os.path.join(self.data_dir, f"{county_fips}_time_series.json")
        
    def add_data_point(self, 
                       county_fips: str, 
                       timestamp: str,
                       metrics: Dict[str, float],
                       metadata: Optional[Dict] = None) -> bool:
        """
        Add a data point to a county's time series.
        
        Args:
            county_fips: County FIPS code
            timestamp: Timestamp for the data point (YYYY-MM-DD or ISO format)
            metrics: Dictionary of metric values
            metadata: Additional metadata for the data point
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Standardize timestamp format
            if not timestamp:
                timestamp = datetime.now().isoformat()
            else:
                # Try to parse the timestamp and standardize
                try:
                    dt = datetime.fromisoformat(timestamp)
                except ValueError:
                    try:
                        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                    except ValueError:
                        try:
                            dt = datetime.strptime(timestamp, "%Y-%m-%d")
                        except ValueError:
                            logger.error(f"Invalid timestamp format: {timestamp}")
                            return False
                timestamp = dt.isoformat()
            
            # Define the data point
            data_point = {
                "timestamp": timestamp,
                "metrics": metrics,
                "metadata": metadata or {}
            }
            
            # Get the file path
            file_path = self.get_county_file_path(county_fips)
            
            # Load existing data or create new
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    time_series_data = json.load(f)
            else:
                time_series_data = {
                    "county_fips": county_fips,
                    "data_points": []
                }
            
            # Add the new data point
            time_series_data["data_points"].append(data_point)
            
            # Sort by timestamp
            time_series_data["data_points"].sort(key=lambda x: x["timestamp"])
            
            # Save the updated data
            with open(file_path, 'w') as f:
                json.dump(time_series_data, f, indent=2)
                
            logger.info(f"Added data point for county {county_fips} at {timestamp}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding data point for county {county_fips}: {e}")
            return False
            
    def get_time_series(self, county_fips: str) -> Dict:
        """
        Get the complete time series for a county.
        
        Args:
            county_fips: County FIPS code
            
        Returns:
            Dictionary with time series data
        """
        try:
            file_path = self.get_county_file_path(county_fips)
            
            if not os.path.exists(file_path):
                logger.warning(f"No time series data found for county {county_fips}")
                return {"county_fips": county_fips, "data_points": []}
                
            with open(file_path, 'r') as f:
                time_series_data = json.load(f)
                
            return time_series_data
            
        except Exception as e:
            logger.error(f"Error getting time series for county {county_fips}: {e}")
            return {"county_fips": county_fips, "data_points": []}
            
    def get_latest_data_point(self, county_fips: str) -> Dict:
        """
        Get the most recent data point for a county.
        
        Args:
            county_fips: County FIPS code
            
        Returns:
            Dictionary with the latest data point
        """
        time_series = self.get_time_series(county_fips)
        
        if not time_series["data_points"]:
            return None
            
        # Sort by timestamp and get the latest
        data_points = sorted(time_series["data_points"], key=lambda x: x["timestamp"])
        return data_points[-1]
        
    def get_data_for_timeframe(self, 
                              county_fips: str, 
                              start_date: str,
                              end_date: str) -> List[Dict]:
        """
        Get data points within a specific timeframe.
        
        Args:
            county_fips: County FIPS code
            start_date: Start date (ISO format or YYYY-MM-DD)
            end_date: End date (ISO format or YYYY-MM-DD)
            
        Returns:
            List of data points within the timeframe
        """
        try:
            time_series = self.get_time_series(county_fips)
            
            if not time_series["data_points"]:
                return []
                
            # Convert dates to datetime objects for comparison
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                
            try:
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Filter data points within the timeframe
            filtered_data = []
            for data_point in time_series["data_points"]:
                try:
                    data_dt = datetime.fromisoformat(data_point["timestamp"])
                    if start_dt <= data_dt <= end_dt:
                        filtered_data.append(data_point)
                except ValueError:
                    logger.warning(f"Invalid timestamp format in data: {data_point['timestamp']}")
                    
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error getting data for timeframe: {e}")
            return []
            
    def export_to_dataframe(self, county_fips: str) -> pd.DataFrame:
        """
        Export time series data to a pandas DataFrame.
        
        Args:
            county_fips: County FIPS code
            
        Returns:
            DataFrame with time series data
        """
        try:
            time_series = self.get_time_series(county_fips)
            
            if not time_series["data_points"]:
                return pd.DataFrame()
                
            # Extract data points
            data = []
            for point in time_series["data_points"]:
                row = {"timestamp": point["timestamp"]}
                # Add metrics as columns
                for metric, value in point["metrics"].items():
                    row[metric] = value
                # Add metadata as additional columns
                for meta_key, meta_value in point["metadata"].items():
                    row[f"meta_{meta_key}"] = meta_value
                data.append(row)
                
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            
            # Set timestamp as index
            df = df.set_index("timestamp").sort_index()
            
            return df
            
        except Exception as e:
            logger.error(f"Error exporting to DataFrame: {e}")
            return pd.DataFrame()
            
    def store_processed_metrics(self, metrics_file: str) -> bool:
        """
        Store processed metrics file in the time series database.
        
        Args:
            metrics_file: Path to the metrics JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load metrics file
            with open(metrics_file, 'r') as f:
                metrics_data = json.load(f)
                
            # Extract required fields
            county_fips = metrics_data.get("county_fips")
            if not county_fips:
                logger.error(f"Missing county_fips in metrics file: {metrics_file}")
                return False
                
            # Get timestamp from collection_date
            timestamp = metrics_data.get("collection_date")
            
            # Get metrics
            metrics = metrics_data.get("metrics", {})
            
            # Get metadata
            metadata = metrics_data.get("metadata", {})
            
            # Add to time series
            return self.add_data_point(
                county_fips=county_fips,
                timestamp=timestamp,
                metrics=metrics,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error storing processed metrics: {e}")
            return False


if __name__ == "__main__":
    # Simple test run
    import argparse
    import glob
    
    parser = argparse.ArgumentParser(description="Manage time series data for counties")
    parser.add_argument('--input', help='Path to metrics JSON file or directory')
    parser.add_argument('--county', help='County FIPS code to query')
    parser.add_argument('--action', choices=['add', 'query', 'latest', 'export'], 
                        default='query', help='Action to perform')
    parser.add_argument('--start-date', help='Start date for timeframe query (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for timeframe query (YYYY-MM-DD)')
    args = parser.parse_args()
    
    ts_store = TimeSeriesStore()
    
    if args.action == 'add' and args.input:
        if os.path.isdir(args.input):
            # Process all metrics files in the directory
            metrics_files = glob.glob(os.path.join(args.input, "*_metrics.json"))
            success_count = 0
            for file in metrics_files:
                if ts_store.store_processed_metrics(file):
                    success_count += 1
            print(f"Added {success_count}/{len(metrics_files)} metrics files to time series")
        else:
            # Process single file
            if ts_store.store_processed_metrics(args.input):
                print(f"Successfully added metrics from {args.input}")
            else:
                print(f"Failed to add metrics from {args.input}")
                
    elif args.action == 'query' and args.county:
        if args.start_date and args.end_date:
            # Query for specific timeframe
            data_points = ts_store.get_data_for_timeframe(
                args.county, args.start_date, args.end_date
            )
            print(f"Found {len(data_points)} data points for county {args.county}")
            for point in data_points:
                timestamp = point["timestamp"]
                metrics = point["metrics"]
                print(f"  {timestamp}: Obsolescence={metrics.get('obsolescence_score', 'N/A'):.4f}, "
                      f"Growth={metrics.get('growth_potential_score', 'N/A'):.4f}")
        else:
            # Query all time series
            time_series = ts_store.get_time_series(args.county)
            print(f"Found {len(time_series['data_points'])} data points for county {args.county}")
            
    elif args.action == 'latest' and args.county:
        # Get latest data point
        latest = ts_store.get_latest_data_point(args.county)
        if latest:
            timestamp = latest["timestamp"]
            metrics = latest["metrics"]
            print(f"Latest data for county {args.county} ({timestamp}):")
            for metric, value in metrics.items():
                print(f"  {metric}: {value:.4f}")
        else:
            print(f"No data found for county {args.county}")
            
    elif args.action == 'export' and args.county:
        # Export to DataFrame
        df = ts_store.export_to_dataframe(args.county)
        if not df.empty:
            print(f"Exported time series for county {args.county}:")
            print(df.head(10))
        else:
            print(f"No data found for county {args.county}")
    else:
        print("Invalid action or missing required arguments")