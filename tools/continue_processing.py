#!/usr/bin/env python3
"""
Continue processing counties with real satellite data from 1000 to 2000 counties.
This script waits for the current processing to reach 1000 counties before starting.
"""

import os
import sys
import argparse
import time
import json
import logging
import subprocess
import numpy as np

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/continue_processing.log')
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Continue processing counties with real satellite data.')
    parser.add_argument('--input-file', type=str, default='data/final/real_county_scores.geojson',
                        help='Path to the input GeoJSON file (being processed by the current script)')
    parser.add_argument('--target-count', type=int, default=2000,
                        help='New target number of counties to process')
    parser.add_argument('--wait-interval', type=int, default=60,
                        help='Interval in seconds to check if current processing has reached 1000 counties')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Number of counties to process in each batch')
    parser.add_argument('--delay', type=int, default=60,
                        help='Delay in seconds between batches')
    return parser.parse_args()

def wait_for_completion(input_file, initial_target=1000, wait_interval=60):
    """
    Wait for the current processing to reach the initial target count.
    
    Args:
        input_file: Path to the input file
        initial_target: Initial target count to wait for
        wait_interval: Interval in seconds to check progress
        
    Returns:
        True when the target is reached
    """
    logger.info(f"Waiting for current processing to reach {initial_target} counties...")
    
    while True:
        if os.path.exists(input_file):
            try:
                with open(input_file, 'r') as f:
                    data = json.load(f)
                    current_count = len(data['features'])
                    logger.info(f"Current progress: {current_count}/{initial_target} counties")
                    
                    if current_count >= initial_target:
                        logger.info(f"Initial target of {initial_target} counties reached!")
                        return True
            except Exception as e:
                logger.error(f"Error checking progress: {e}")
        
        logger.info(f"Waiting {wait_interval} seconds before checking again...")
        time.sleep(wait_interval)

def main():
    """Main function to continue processing counties after the initial target is reached."""
    args = parse_args()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Wait for the current processing to reach 1000 counties
    wait_for_completion(args.input_file, initial_target=1000, wait_interval=args.wait_interval)
    
    # Start the new processing with a target of 2000 counties
    logger.info(f"Starting new processing with target of {args.target_count} counties")
    
    # Build the command to run the continuous_real_processing.py script
    cmd = [
        'python', 'tools/continuous_real_processing.py',
        '--target-count', str(args.target_count),
        '--batch-size', str(args.batch_size),
        '--delay', str(args.delay),
        '--output', args.input_file
    ]
    
    # Run the command
    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        logger.info("Processing completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running continuous processing: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
