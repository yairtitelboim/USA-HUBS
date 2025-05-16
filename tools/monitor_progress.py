#!/usr/bin/env python3
"""
Monitor the progress of the continuous processing script and update the mapbox_shapefile_counties.html file.
"""

import os
import sys
import time
import json
import numpy as np
import logging
import re
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/monitor_progress.log')
    ]
)
logger = logging.getLogger(__name__)

def get_current_progress(geojson_file):
    """
    Get the current progress from the GeoJSON file.
    
    Args:
        geojson_file: Path to the GeoJSON file
        
    Returns:
        Dictionary with progress information
    """
    try:
        # Load the data
        data = json.load(open(geojson_file))
        
        # Extract scores
        scores = [f['properties']['obsolescence_score'] for f in data['features']]
        confidences = [f['properties']['confidence'] for f in data['features']]
        tile_counts = [f['properties']['tile_count'] for f in data['features']]
        
        # Get state distribution
        states = {}
        for feature in data['features']:
            state = feature['properties'].get('STATEFP', 'Unknown')
            states[state] = states.get(state, 0) + 1
        
        # Calculate metrics
        metrics = {
            'total_counties': len(data['features']),
            'avg_score': np.mean(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'median_score': np.median(scores),
            'avg_confidence': np.mean(confidences),
            'avg_tile_count': np.mean(tile_counts),
            'min_tile_count': min(tile_counts),
            'max_tile_count': max(tile_counts),
            'states': states
        }
        
        return metrics
    except Exception as e:
        logger.error(f"Error getting current progress: {e}")
        return None

def update_html_file(html_file, metrics, target_count):
    """
    Update the HTML file with the current progress.
    
    Args:
        html_file: Path to the HTML file
        metrics: Dictionary with progress metrics
        target_count: Target number of counties
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        # Read the HTML file
        with open(html_file, 'r') as f:
            html = f.read()
        
        # Update the disclaimer
        disclaimer_pattern = r'<div id="disclaimer">\s*<strong>Data Coverage:</strong>.*?</div>'
        new_disclaimer = f'<div id="disclaimer">\n    <strong>Data Coverage:</strong> This map displays real obsolescence scores for {metrics["total_counties"]} counties across the United States, using only real satellite data. Processing continues to reach {target_count} counties ({metrics["total_counties"]/target_count*100:.1f}% complete).\n  </div>'
        
        html = re.sub(disclaimer_pattern, new_disclaimer, html, flags=re.DOTALL)
        
        # Write the updated HTML file
        with open(html_file, 'w') as f:
            f.write(html)
        
        return True
    except Exception as e:
        logger.error(f"Error updating HTML file: {e}")
        return False

def main():
    """Main function to monitor progress and update the HTML file."""
    # Configuration
    geojson_file = 'data/final/real_county_scores.geojson'
    html_file = 'mapbox_shapefile_counties.html'
    target_count = 1000
    check_interval = 60  # seconds
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    logger.info(f"Starting monitoring of {geojson_file}")
    logger.info(f"Target count: {target_count} counties")
    logger.info(f"Check interval: {check_interval} seconds")
    
    # Main monitoring loop
    while True:
        # Get current progress
        metrics = get_current_progress(geojson_file)
        
        if metrics:
            # Log progress
            logger.info(f"Current progress: {metrics['total_counties']}/{target_count} counties ({metrics['total_counties']/target_count*100:.1f}%)")
            logger.info(f"Average score: {metrics['avg_score']:.2f}, Range: {metrics['min_score']:.2f}-{metrics['max_score']:.2f}, Median: {metrics['median_score']:.2f}")
            
            # Update HTML file
            if update_html_file(html_file, metrics, target_count):
                logger.info(f"Updated {html_file}")
            
            # Check if we've reached the target
            if metrics['total_counties'] >= target_count:
                logger.info(f"Reached target count of {target_count} counties")
                break
        
        # Wait for the next check
        logger.info(f"Waiting {check_interval} seconds for next check...")
        time.sleep(check_interval)

if __name__ == "__main__":
    main()
