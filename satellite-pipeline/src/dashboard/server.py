#!/usr/bin/env python3
"""
Satellite Data Dashboard Server

This module provides a simple Flask server for the dashboard that shows
time series data from the satellite data collection pipeline.
"""

import os
import sys
import yaml
import logging
import requests
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta

from flask import Flask, render_template, request, jsonify

# Configure logging
log_dir = Path(__file__).parents[2] / 'logs'
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'dashboard.log')
    ]
)
logger = logging.getLogger('dashboard')

# Load settings
def load_settings():
    settings_path = Path(__file__).parents[2] / 'config' / 'settings.yaml'
    with open(settings_path, 'r') as f:
        return yaml.safe_load(f)

settings = load_settings()

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)

# API endpoint configuration
API_HOST = settings['api']['host']
API_PORT = 8001  # Use our new port
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"
API_PREFIX = settings['api']['endpoint_prefix']

def get_api_url(endpoint):
    """Get full API URL for an endpoint."""
    return f"{API_BASE_URL}{API_PREFIX}/{endpoint}"

@app.route('/')
def index():
    """Render the dashboard homepage."""
    return render_template('index.html')

@app.route('/api/v1/counties')
def get_counties():
    """Get list of counties with data."""
    try:
        # Get all time series files directly instead of calling API
        time_series_dir = Path(__file__).parents[2] / 'data' / 'processed' / 'time_series'
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
        
        return jsonify({"counties": counties})
    except Exception as e:
        logger.error(f"Error getting counties: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/time_series/<county_fips>')
def get_time_series(county_fips):
    """Get time series data for a county."""
    try:
        # Get the time series data directly from file
        time_series_path = Path(__file__).parents[2] / 'data' / 'processed' / 'time_series' / f"{county_fips}_time_series.json"
        
        if not time_series_path.exists():
            return jsonify({"error": f"No data found for county {county_fips}"}), 404
            
        with open(time_series_path, 'r') as f:
            time_series = json.load(f)
        
        # Filter by date range if provided
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date or end_date:
            # Set defaults if not provided
            end_date = end_date or datetime.now().isoformat()
            # Default start date is 1 year ago
            if not start_date:
                start_dt = datetime.now() - timedelta(days=365)
                start_date = start_dt.isoformat()
                
            # Convert dates to datetime objects for comparison
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                except ValueError:
                    raise ValueError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD format.")
                
            try:
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                except ValueError:
                    raise ValueError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD format.")
            
            # Filter data points within the timeframe
            filtered_data = []
            for data_point in time_series["data_points"]:
                try:
                    data_dt = datetime.fromisoformat(data_point["timestamp"])
                    if start_dt <= data_dt <= end_dt:
                        filtered_data.append(data_point)
                except ValueError:
                    logger.warning(f"Invalid timestamp format in data: {data_point['timestamp']}")
                    
            time_series["data_points"] = filtered_data
        
        return jsonify(time_series)
    except ValueError as e:
        logger.error(f"Error getting time series for county {county_fips}: {e}")
        return jsonify({"error": str(e)}), 400  # Bad request for invalid parameters
    except Exception as e:
        logger.error(f"Error getting time series for county {county_fips}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/latest/<county_fips>')
def get_latest(county_fips):
    """Get latest data point for a county."""
    try:
        # Get the time series data directly from file
        time_series_path = Path(__file__).parents[2] / 'data' / 'processed' / 'time_series' / f"{county_fips}_time_series.json"
        
        if not time_series_path.exists():
            return jsonify({"error": f"No data found for county {county_fips}"}), 404
            
        with open(time_series_path, 'r') as f:
            time_series = json.load(f)
            
        if not time_series["data_points"]:
            return jsonify({"error": f"No data points for county {county_fips}"}), 404
            
        # Sort by timestamp and get the latest
        data_points = sorted(time_series["data_points"], key=lambda x: x["timestamp"])
        latest = data_points[-1]
        
        return jsonify({
            "county_fips": county_fips,
            "latest_data": latest,
            "data_point_count": len(time_series["data_points"])
        })
    except Exception as e:
        logger.error(f"Error getting latest data for county {county_fips}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/metrics')
def get_metrics():
    """Get metrics for all counties for a date."""
    try:
        date = request.args.get('date')
        metric = request.args.get('metric')
        
        if not date or not metric:
            return jsonify({"error": "Date and metric parameters are required"}), 400
        
        response = requests.get(
            get_api_url('metrics'),
            params={'date': date, 'metric': metric}
        )
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Satellite Data Dashboard Server")
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind the dashboard server')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind the dashboard server')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    logger.info(f"Starting dashboard server at {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug) 