#!/usr/bin/env python3
"""
Real-time monitoring of county processing progress.
Displays a progress bar and estimated time remaining.
"""

import os
import sys
import time
import json
import argparse
import datetime
from tqdm import tqdm

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Monitor county processing progress in real-time.')
    parser.add_argument('--file', type=str, default='data/final/county_scores.geojson',
                        help='Path to the GeoJSON file to monitor')
    parser.add_argument('--target', type=int, default=3000,
                        help='Target number of counties')
    parser.add_argument('--interval', type=int, default=5,
                        help='Interval in seconds between updates')
    parser.add_argument('--log-file', type=str, default='logs/add_1000_more_counties_output.log',
                        help='Path to the log file to monitor for current processing')
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
        print(f"File {file_path} does not exist")
        return None
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            count = len(data['features'])
            return count
    except json.JSONDecodeError:
        print(f"File {file_path} is not valid JSON or is being written to")
        return None
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def get_current_processing_info(log_file):
    """
    Get information about the current county being processed from the log file.
    
    Args:
        log_file: Path to the log file
        
    Returns:
        Dictionary with information about the current processing
    """
    if not os.path.exists(log_file):
        return None
    
    try:
        # Get the last 50 lines of the log file
        with open(log_file, 'r') as f:
            lines = f.readlines()
            last_lines = lines[-50:]
        
        # Look for the current county being processed
        current_county = None
        for line in reversed(last_lines):
            if "Processing county:" in line:
                parts = line.split("Processing county:")
                if len(parts) > 1:
                    current_county = parts[1].strip()
                    break
        
        # Look for the current batch progress
        batch_progress = None
        for line in reversed(last_lines):
            if "Processing county " in line and " in current batch" in line:
                parts = line.split("Processing county ")[1].split(" in current batch")[0]
                batch_progress = parts.strip()
                break
        
        # Look for the estimated time remaining
        time_remaining = None
        for line in reversed(last_lines):
            if "Estimated time remaining for batch:" in line:
                parts = line.split("Estimated time remaining for batch:")[1]
                time_remaining = parts.strip()
                break
        
        # Look for the overall progress
        overall_progress = None
        for line in reversed(last_lines):
            if "Overall progress:" in line:
                parts = line.split("Overall progress:")[1].split("counties processed")[0]
                overall_progress = parts.strip()
                break
        
        # Look for the overall estimated time remaining
        overall_time_remaining = None
        for line in reversed(last_lines):
            if "Estimated time remaining:" in line:
                parts = line.split("Estimated time remaining:")[1]
                overall_time_remaining = parts.strip()
                break
        
        return {
            'current_county': current_county,
            'batch_progress': batch_progress,
            'time_remaining': time_remaining,
            'overall_progress': overall_progress,
            'overall_time_remaining': overall_time_remaining
        }
    except Exception as e:
        print(f"Error reading log file: {e}")
        return None

def main():
    """Main function to monitor progress in real-time."""
    args = parse_args()
    
    print(f"Monitoring county processing progress in real-time")
    print(f"File: {args.file}")
    print(f"Target: {args.target} counties")
    print(f"Update interval: {args.interval} seconds")
    print(f"Log file: {args.log_file}")
    print("\nPress Ctrl+C to stop monitoring\n")
    
    # Initialize progress bar
    pbar = tqdm(total=args.target, desc="Processing counties")
    
    # Initialize variables for tracking progress
    last_count = 0
    start_time = time.time()
    counts_history = []
    
    try:
        while True:
            # Get current count
            current_count = get_current_count(args.file)
            
            if current_count is not None:
                # Update progress bar
                pbar.n = current_count
                pbar.refresh()
                
                # Calculate progress percentage
                progress_percent = current_count / args.target * 100
                
                # Calculate processing rate
                if last_count > 0 and current_count > last_count:
                    # Add to history
                    counts_history.append((time.time(), current_count))
                    
                    # Keep only the last 10 data points
                    if len(counts_history) > 10:
                        counts_history.pop(0)
                    
                    # Calculate rate based on history
                    if len(counts_history) > 1:
                        first_time, first_count = counts_history[0]
                        last_time, last_count = counts_history[-1]
                        time_diff = last_time - first_time
                        count_diff = last_count - first_count
                        
                        if time_diff > 0:
                            rate = count_diff / time_diff
                            remaining_counties = args.target - current_count
                            estimated_time_remaining = remaining_counties / rate if rate > 0 else 0
                            
                            # Format as hours, minutes, seconds
                            hours, remainder = divmod(estimated_time_remaining, 3600)
                            minutes, seconds = divmod(remainder, 60)
                            
                            # Get current processing info
                            processing_info = get_current_processing_info(args.log_file)
                            
                            # Clear the line
                            print("\033[K", end="\r")
                            
                            # Print progress information
                            print(f"Progress: {current_count}/{args.target} counties ({progress_percent:.1f}%)")
                            print(f"Processing rate: {rate:.2f} counties/second")
                            print(f"Estimated time remaining: {int(hours)}h {int(minutes)}m {int(seconds)}s")
                            
                            if processing_info:
                                if processing_info['current_county']:
                                    print(f"Current county: {processing_info['current_county']}")
                                if processing_info['batch_progress']:
                                    print(f"Batch progress: {processing_info['batch_progress']}")
                                if processing_info['time_remaining']:
                                    print(f"Batch time remaining: {processing_info['time_remaining']}")
                                if processing_info['overall_progress']:
                                    print(f"Overall progress: {processing_info['overall_progress']}")
                                if processing_info['overall_time_remaining']:
                                    print(f"Overall time remaining: {processing_info['overall_time_remaining']}")
                            
                            # Move cursor back up
                            lines_to_move = 3 + sum(1 for v in (processing_info or {}).values() if v)
                            print(f"\033[{lines_to_move}A", end="")
                
                # Update last count
                last_count = current_count
                
                # Check if we've reached the target
                if current_count >= args.target:
                    print("\nTarget count reached!")
                    break
            
            # Wait for the next update
            time.sleep(args.interval)
    
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    
    finally:
        # Close the progress bar
        pbar.close()
        
        # Print final statistics
        elapsed_time = time.time() - start_time
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        print(f"\nFinal count: {last_count}/{args.target} counties ({last_count/args.target*100:.1f}%)")
        print(f"Elapsed time: {int(hours)}h {int(minutes)}m {int(seconds)}s")

if __name__ == "__main__":
    main()
