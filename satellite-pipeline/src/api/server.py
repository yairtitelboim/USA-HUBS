#!/usr/bin/env python3
"""
Satellite Data API Server

This module provides a FastAPI server for accessing the satellite data
time series from the county visualization app.
"""

import os
import sys
import json
import yaml
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parents[2]))

# Import our modules
from src.utils.time_series import TimeSeriesStore

# Configure logging
log_dir = Path(__file__).parents[2] / 'logs'
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'api.log')
    ]
)
logger = logging.getLogger('satellite_api')

# Load settings
def load_settings():
    settings_path = Path(__file__).parents[2] / 'config' / 'settings.yaml'
    with open(settings_path, 'r') as f:
        return yaml.safe_load(f)

settings = load_settings()
ts_store = TimeSeriesStore(data_dir=settings['storage']['time_series_dir'])

# Define API models
class MetricsData(BaseModel):
    obsolescence_score: Optional[float] = None
    growth_potential_score: Optional[float] = None
    bivariate_score: Optional[float] = None

class DataPoint(BaseModel):
    timestamp: str
    metrics: MetricsData
    metadata: Dict = {}

class CountyTimeSeries(BaseModel):
    county_fips: str
    county_name: Optional[str] = None
    state_fips: Optional[str] = None
    data_points: List[DataPoint]

# Initialize FastAPI application
app = FastAPI(
    title="Satellite Data Time Series API",
    description="API for accessing time series data of county metrics derived from satellite imagery",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Satellite Data Time Series API",
        "version": "1.0.0",
        "endpoints": {
            "time_series": "/api/v1/time_series/{county_fips}",
            "latest": "/api/v1/latest/{county_fips}",
            "counties": "/api/v1/counties"
        }
    }

@app.get("/api/v1/counties")
async def get_counties():
    """Get a list of all counties with available data"""
    try:
        # List all files in the time series directory
        time_series_dir = Path(ts_store.data_dir)
        county_files = list(time_series_dir.glob("*_time_series.json"))
        
        counties = []
        for file_path in county_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                county_fips = data.get("county_fips")
                # Try to extract the county name from the first data point's metadata
                county_name = None
                state_fips = None
                
                if data["data_points"]:
                    metadata = data["data_points"][0].get("metadata", {})
                    if "county_name" in metadata:
                        county_name = metadata["county_name"]
                    if "state_fips" in metadata:
                        state_fips = metadata["state_fips"]
                
                # Add to counties list with latest timestamp 
                latest_timestamp = max(
                    [dp["timestamp"] for dp in data["data_points"]]
                ) if data["data_points"] else None
                
                counties.append({
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "state_fips": state_fips,
                    "data_point_count": len(data["data_points"]),
                    "latest_timestamp": latest_timestamp
                })
            except Exception as e:
                logger.error(f"Error processing county file {file_path}: {e}")
        
        return {"counties": counties}
    except Exception as e:
        logger.error(f"Error getting counties: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/time_series/{county_fips}")
async def get_time_series(
    county_fips: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get time series data for a specific county"""
    try:
        # Get the time series data
        time_series = ts_store.get_time_series(county_fips)
        
        if not time_series["data_points"]:
            raise HTTPException(status_code=404, detail=f"No data found for county {county_fips}")

        # Filter by date range if provided
        if start_date or end_date:
            # Set defaults if not provided
            end_date = end_date or datetime.now().isoformat()
            # Default start date is 1 year ago
            if not start_date:
                start_dt = datetime.now() - timedelta(days=365)
                start_date = start_dt.isoformat()
                
            filtered_data = ts_store.get_data_for_timeframe(
                county_fips=county_fips,
                start_date=start_date,
                end_date=end_date
            )
            
            time_series["data_points"] = filtered_data
        
        return time_series
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting time series for county {county_fips}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/latest/{county_fips}")
async def get_latest(county_fips: str):
    """Get the latest data point for a specific county"""
    try:
        # Get the latest data point
        latest = ts_store.get_latest_data_point(county_fips)
        
        if not latest:
            raise HTTPException(status_code=404, detail=f"No data found for county {county_fips}")
        
        # Get the full time series to extract county metadata
        time_series = ts_store.get_time_series(county_fips)
        
        return {
            "county_fips": county_fips,
            "latest_data": latest,
            "data_point_count": len(time_series["data_points"])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest data for county {county_fips}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/metrics")
async def get_metrics_by_date(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    metric: str = Query(..., description="Metric name (obsolescence_score, growth_potential_score, bivariate_score)")
):
    """Get metrics for all counties for a specific date"""
    try:
        # Parse the date
        try:
            query_date = datetime.fromisoformat(date) if 'T' in date else datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {date}. Use YYYY-MM-DD.")
        
        # List all files in the time series directory
        time_series_dir = Path(ts_store.data_dir)
        county_files = list(time_series_dir.glob("*_time_series.json"))
        
        results = []
        for file_path in county_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                county_fips = data.get("county_fips")
                
                # Find the closest data point to the requested date
                closest_data_point = None
                min_diff = timedelta.max
                
                for dp in data["data_points"]:
                    dp_date = datetime.fromisoformat(dp["timestamp"]) if 'T' in dp["timestamp"] else datetime.strptime(dp["timestamp"], "%Y-%m-%d")
                    diff = abs(dp_date - query_date)
                    
                    if diff < min_diff:
                        min_diff = diff
                        closest_data_point = dp
                
                # Only include if the closest data point is within 30 days of the requested date
                if closest_data_point and min_diff <= timedelta(days=30):
                    metric_value = closest_data_point.get("metrics", {}).get(metric)
                    
                    if metric_value is not None:
                        results.append({
                            "county_fips": county_fips,
                            "timestamp": closest_data_point["timestamp"],
                            "metric": metric,
                            "value": metric_value
                        })
            except Exception as e:
                logger.error(f"Error processing county file {file_path} for metrics: {e}")
        
        return {"date": date, "metric": metric, "county_metrics": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics for date {date}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="Satellite Data API Server")
    parser.add_argument('--host', default=settings['api']['host'], help='Host to bind the API server')
    parser.add_argument('--port', type=int, default=settings['api']['port'], help='Port to bind the API server')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')
    args = parser.parse_args()
    
    logger.info(f"Starting API server at {args.host}:{args.port}")
    uvicorn.run("server:app", host=args.host, port=args.port, reload=args.reload) 