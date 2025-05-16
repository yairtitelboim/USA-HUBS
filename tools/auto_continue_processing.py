#!/usr/bin/env python3
"""
Automatically monitor the current county processing and launch the next 1000 counties
when the target of 2000 is reached.
"""

import os
import sys
import time
import json
import logging
import subprocess
import argparse
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/auto_continue_processing.log')
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Automatically continue processing after reaching 2000 counties.')
    parser.add_argument('--monitor-file', type=str, default='data/final/real_county_scores.geojson',
                        help='Path to the GeoJSON file to monitor')
    parser.add_argument('--target-count', type=int, default=2000,
                        help='Target count to trigger the next phase')
    parser.add_argument('--check-interval', type=int, default=300,
                        help='Interval in seconds between checks')
    parser.add_argument('--additional-count', type=int, default=1000,
                        help='Number of additional counties to process in the next phase')
    return parser.parse_args()

def get_current_count(file_path):
    """
    Get the current count of counties in the GeoJSON file.
    
    Args:
        file_path: Path to the GeoJSON file
        
    Returns:
        Current count of counties, or None if the file cannot be read
    """
    if not os.path.exists(file_path):
        logger.warning(f"File {file_path} does not exist")
        return None
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            count = len(data['features'])
            return count
    except json.JSONDecodeError:
        logger.warning(f"File {file_path} is not valid JSON or is being written to")
        return None
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None

def is_process_running(process_name):
    """
    Check if a process with the given name is running.
    
    Args:
        process_name: Name of the process to check
        
    Returns:
        True if the process is running, False otherwise
    """
    try:
        # Use ps command to check if the process is running
        cmd = f"ps aux | grep '{process_name}' | grep -v grep | wc -l"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        count = int(result.stdout.strip())
        return count > 0
    except Exception as e:
        logger.error(f"Error checking if process {process_name} is running: {e}")
        return False

def launch_next_phase(additional_count):
    """
    Launch the script to process additional counties.
    
    Args:
        additional_count: Number of additional counties to process
        
    Returns:
        True if the script was launched successfully, False otherwise
    """
    logger.info(f"Launching script to process {additional_count} more counties")
    
    try:
        # Build the command
        cmd = [
            'python', 'tools/add_1000_more_counties.py',
            '--additional-count', str(additional_count)
        ]
        
        # Launch the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"Successfully launched process with PID {process.pid}")
        return True
    except Exception as e:
        logger.error(f"Error launching next phase: {e}")
        return False

def main():
    """Main function to monitor and automatically continue processing."""
    args = parse_args()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    logger.info("Starting automatic monitoring")
    logger.info(f"Monitoring file: {args.monitor_file}")
    logger.info(f"Target count: {args.target_count}")
    logger.info(f"Check interval: {args.check_interval} seconds")
    logger.info(f"Additional count for next phase: {args.additional_count}")
    
    # Main monitoring loop
    while True:
        # Check if the continuous_real_processing.py script is still running
        if not is_process_running('continuous_real_processing.py'):
            # Get the current count
            current_count = get_current_count(args.monitor_file)
            
            if current_count is not None:
                logger.info(f"Current count: {current_count}/{args.target_count}")
                
                # Check if we've reached the target
                if current_count >= args.target_count:
                    logger.info(f"Target count of {args.target_count} reached!")
                    
                    # Launch the next phase
                    if launch_next_phase(args.additional_count):
                        logger.info("Next phase launched successfully")
                        break
                    else:
                        logger.error("Failed to launch next phase")
                        # Wait a bit and try again
                        time.sleep(60)
                else:
                    logger.info(f"Target count not reached yet. Waiting for the process to continue or restart.")
                    time.sleep(args.check_interval)
            else:
                logger.warning("Could not determine current count. Will check again later.")
                time.sleep(args.check_interval)
        else:
            # The process is still running, check the current count
            current_count = get_current_count(args.monitor_file)
            
            if current_count is not None:
                logger.info(f"Current count: {current_count}/{args.target_count} (Process is running)")
                
                # If we've already reached the target but the process is still running,
                # it might be finishing up. Wait for it to complete.
                if current_count >= args.target_count:
                    logger.info(f"Target count reached, but process is still running. Waiting for it to complete.")
            
            # Wait for the next check
            time.sleep(args.check_interval)
    
    logger.info("Monitoring complete")

if __name__ == "__main__":
    main()
