#!/usr/bin/env python3
"""
Simple script to check the current progress of county processing.
"""

import os
import json
import subprocess

def get_current_count(file_path):
    """Get the current count of counties in the GeoJSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return len(data['features'])
    except Exception as e:
        print(f"Error reading file: {e}")

        # Try using grep as a fallback
        try:
            import subprocess
            cmd = f"grep -o '\"GEOID\":' {file_path} | wc -l"
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            count = int(result.stdout.strip())
            print(f"Using grep fallback: found {count} counties")
            return count
        except Exception as e2:
            print(f"Grep fallback also failed: {e2}")
            return None

def get_recent_log_entries(log_file, num_lines=20):
    """Get the most recent log entries."""
    try:
        result = subprocess.run(['tail', '-n', str(num_lines), log_file],
                               capture_output=True, text=True, check=True)
        return result.stdout
    except Exception as e:
        print(f"Error reading log file: {e}")
        return None

def main():
    """Main function."""
    # Configuration
    geojson_file = 'data/final/county_scores.geojson'
    log_file = 'logs/add_1000_more_counties_output.log'
    target_count = 3000

    # Get current count
    current_count = get_current_count(geojson_file)

    if current_count is not None:
        # Calculate progress
        progress_percent = current_count / target_count * 100

        # Print progress information
        print(f"\n=== COUNTY PROCESSING PROGRESS ===")
        print(f"Current count: {current_count}/{target_count} counties ({progress_percent:.1f}%)")
        print(f"Remaining: {target_count - current_count} counties")

        # Get and print recent log entries
        print(f"\n=== RECENT LOG ENTRIES ===")
        recent_logs = get_recent_log_entries(log_file)
        if recent_logs:
            print(recent_logs)
    else:
        print("Could not determine current progress.")

if __name__ == "__main__":
    main()
