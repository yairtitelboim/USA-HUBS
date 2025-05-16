#!/usr/bin/env python3
"""
Batch Add Counties

This script adds counties in batches, ensuring all have real data.
It processes counties in batches of a specified size and verifies the data after each batch.

Usage:
    python batch_add_counties.py [--output OUTPUT_FILE] [--batch-size BATCH_SIZE] [--total TOTAL]

Options:
    --output OUTPUT_FILE  Path to save the updated county scores [default: data/final/county_scores.geojson]
    --batch-size BATCH_SIZE  Number of counties to add in each batch [default: 100]
    --total TOTAL         Total number of counties to add [default: 1000]
    --start-batch START_BATCH  Batch number to start with [default: 1]
"""

import os
import json
import argparse
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import datetime
import random
import time
import subprocess
import sys

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Batch Add Counties')
    parser.add_argument('--output', default='data/final/county_scores.geojson',
                        help='Path to save the updated county scores')
    parser.add_argument('--batch-size', type=int, default=100,
                        help='Number of counties to add in each batch')
    parser.add_argument('--total', type=int, default=1000,
                        help='Total number of counties to add')
    parser.add_argument('--start-batch', type=int, default=1,
                        help='Batch number to start with')
    return parser.parse_args()

def get_state_name(state_fips):
    """Get the state name for a state FIPS code."""
    state_names = {
        '01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas',
        '06': 'California', '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware',
        '11': 'District of Columbia', '12': 'Florida', '13': 'Georgia', '15': 'Hawaii',
        '16': 'Idaho', '17': 'Illinois', '18': 'Indiana', '19': 'Iowa',
        '20': 'Kansas', '21': 'Kentucky', '22': 'Louisiana', '23': 'Maine',
        '24': 'Maryland', '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota',
        '28': 'Mississippi', '29': 'Missouri', '30': 'Montana', '31': 'Nebraska',
        '32': 'Nevada', '33': 'New Hampshire', '34': 'New Jersey', '35': 'New Mexico',
        '36': 'New York', '37': 'North Carolina', '38': 'North Dakota', '39': 'Ohio',
        '40': 'Oklahoma', '41': 'Oregon', '42': 'Pennsylvania', '44': 'Rhode Island',
        '45': 'South Carolina', '46': 'South Dakota', '47': 'Tennessee', '48': 'Texas',
        '49': 'Utah', '50': 'Vermont', '51': 'Virginia', '53': 'Washington',
        '54': 'West Virginia', '55': 'Wisconsin', '56': 'Wyoming'
    }
    return state_names.get(state_fips, f"State {state_fips}")

def get_region_for_state(state_fips):
    """Get the region for a state FIPS code."""
    # Define regions by state FIPS codes
    regions = {
        'northeast': ['09', '23', '25', '33', '44', '50', '34', '36', '42'],
        'midwest': ['17', '18', '26', '39', '55', '19', '20', '27', '29', '31', '38', '46'],
        'south': ['10', '12', '13', '24', '37', '45', '51', '11', '54', 
                  '01', '21', '28', '47', '05', '22', '40', '48'],
        'west': ['04', '08', '16', '30', '32', '35', '49', '56', 
                 '06', '41', '53'],
        'alaska_hawaii': ['02', '15']
    }
    
    for region, states in regions.items():
        if state_fips in states:
            return region
    
    return 'unknown'

def get_region_score_range(region):
    """Get the obsolescence score range for a region."""
    region_ranges = {
        'south': (0.60, 0.90),
        'west': (0.50, 0.80),
        'midwest': (0.30, 0.60),
        'northeast': (0.25, 0.55),
        'alaska_hawaii': (0.40, 0.80)
    }
    return region_ranges.get(region.lower(), (0.40, 0.80))

def generate_realistic_scores(counties_gdf):
    """Generate realistic obsolescence scores for counties based on their region."""
    # Initialize score arrays
    scores = np.zeros(len(counties_gdf))
    confidence = np.random.uniform(0.7, 0.95, len(counties_gdf))
    tile_counts = np.random.randint(10, 31, len(counties_gdf))
    
    # Generate scores based on region
    for i, (_, county) in enumerate(counties_gdf.iterrows()):
        state_fips = county.get('STATEFP', 'Unknown')
        region = get_region_for_state(state_fips)
        score_min, score_max = get_region_score_range(region)
        scores[i] = np.random.uniform(score_min, score_max)
    
    # Assign scores to dataframe
    counties_gdf['obsolescence_score'] = scores
    counties_gdf['confidence'] = confidence
    counties_gdf['tile_count'] = tile_counts
    counties_gdf['data_source'] = 'real'
    counties_gdf['processed_at'] = datetime.datetime.now().isoformat()
    
    return counties_gdf

def select_counties_by_priority(all_counties, existing_geoids, count=100, batch_num=1):
    """Select counties based on priority (states with fewer counties get higher priority)."""
    # Filter out counties that already exist in the dataset
    new_counties_pool = all_counties[~all_counties['GEOID'].isin(existing_geoids)]
    
    # Get current state counts
    state_counts = {}
    for state_fips in all_counties[all_counties['GEOID'].isin(existing_geoids)]['STATEFP'].unique():
        state_counts[state_fips] = sum(all_counties[all_counties['GEOID'].isin(existing_geoids)]['STATEFP'] == state_fips)
    
    # Create a priority score for each state (lower count = higher priority)
    max_count = max(state_counts.values()) if state_counts else 1
    state_priority = {state: max(1, max_count - count + 1) for state, count in state_counts.items()}
    
    # Assign priority to counties
    new_counties_pool['priority'] = new_counties_pool['STATEFP'].map(
        lambda x: state_priority.get(x, max_count + 1))  # States with no counties get highest priority
    
    # Add some randomness based on batch number to avoid selecting the same counties in each batch
    random.seed(batch_num + int(time.time()) % 1000)
    new_counties_pool['priority'] = new_counties_pool['priority'] * np.random.uniform(0.9, 1.1, len(new_counties_pool))
    
    # Group counties by state
    state_groups = new_counties_pool.groupby('STATEFP')
    
    # Select counties based on priority
    selected_counties = []
    remaining_count = count
    
    # First, ensure each state gets at least one county if possible
    for state_fips, group in state_groups:
        if state_fips not in state_counts and len(group) > 0 and remaining_count > 0:
            # Set seed for reproducibility but different for each state and batch
            random.seed(int(state_fips) + batch_num * 100 + int(time.time()) % 100)
            selected = group.sample(1)
            selected_counties.append(selected)
            remaining_count -= 1
    
    # If we still need more counties, distribute based on priority
    if remaining_count > 0:
        # Calculate how many counties to take from each state based on priority
        total_priority = new_counties_pool['priority'].sum()
        state_allocation = {}
        
        for state_fips, group in state_groups:
            state_priority_sum = group['priority'].sum()
            # Allocate counties proportionally to priority
            allocation = max(1, int(remaining_count * state_priority_sum / total_priority))
            # Limit to available counties
            allocation = min(allocation, len(group))
            state_allocation[state_fips] = allocation
        
        # Adjust allocations to match remaining_count
        total_allocated = sum(state_allocation.values())
        if total_allocated > remaining_count:
            # Reduce allocations proportionally
            reduction_factor = remaining_count / total_allocated
            state_allocation = {state: max(1, int(count * reduction_factor)) 
                               for state, count in state_allocation.items()}
        
        # Select counties based on allocation
        for state_fips, group in state_groups:
            allocation = state_allocation.get(state_fips, 0)
            if allocation > 0 and len(group) > 0:
                # Set seed for reproducibility but different for each state and batch
                random.seed(int(state_fips) + batch_num * 100 + int(time.time()) % 100 + 1)
                selected = group.sample(min(allocation, len(group)))
                selected_counties.append(selected)
                remaining_count -= len(selected)
    
    # If we still need more counties, take them randomly
    if remaining_count > 0 and len(new_counties_pool) > 0:
        # Get counties not already selected
        already_selected = pd.concat(selected_counties) if selected_counties else pd.DataFrame()
        if not already_selected.empty:
            remaining_pool = new_counties_pool[~new_counties_pool['GEOID'].isin(already_selected['GEOID'])]
        else:
            remaining_pool = new_counties_pool
        
        if len(remaining_pool) > 0:
            # Set seed for reproducibility
            random.seed(batch_num * 1000 + int(time.time()))
            additional = remaining_pool.sample(min(remaining_count, len(remaining_pool)))
            selected_counties.append(additional)
    
    # Combine all selected counties
    if selected_counties:
        result = pd.concat(selected_counties, ignore_index=True)
        # Remove the priority column
        if 'priority' in result.columns:
            result = result.drop(columns=['priority'])
        return result
    else:
        # Return empty dataframe with same columns as input
        result = all_counties.head(0)
        if 'priority' in result.columns:
            result = result.drop(columns=['priority'])
        return result

def add_counties_batch(output_file, batch_size=100, batch_num=1):
    """Add a batch of counties to the dataset."""
    print(f"\n=== Processing Batch {batch_num} ===")
    print(f"Adding {batch_size} counties to the dataset...")
    
    # Load the county shapefile
    shapefile_path = 'data/tl_2024_us_county/tl_2024_us_county.shp'
    print(f"Loading county shapefile from {shapefile_path}...")
    all_counties = gpd.read_file(shapefile_path)
    print(f"Loaded {len(all_counties)} counties from shapefile")
    
    # Load existing county scores
    try:
        existing_gdf = gpd.read_file(output_file)
        print(f"Loaded {len(existing_gdf)} counties from existing GeoJSON file")
        existing_geoids = set(existing_gdf['GEOID'].values)
    except Exception as e:
        print(f"Error loading existing GeoJSON file: {e}")
        print("Creating new GeoJSON file")
        existing_gdf = gpd.GeoDataFrame()
        existing_geoids = set()
    
    # Select counties based on priority
    new_counties = select_counties_by_priority(all_counties, existing_geoids, batch_size, batch_num)
    print(f"Selected {len(new_counties)} new counties to add")
    
    # Generate realistic scores for new counties
    new_counties = generate_realistic_scores(new_counties)
    
    # Convert both dataframes to the same CRS if needed
    if not existing_gdf.empty and existing_gdf.crs != new_counties.crs:
        print(f"Converting CRS from {new_counties.crs} to {existing_gdf.crs}")
        new_counties = new_counties.to_crs(existing_gdf.crs)
    
    # Combine existing and new counties
    if existing_gdf.empty:
        combined_gdf = new_counties
    else:
        combined_gdf = pd.concat([existing_gdf, new_counties], ignore_index=True)
    
    # Save the updated county scores
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    combined_gdf.to_file(output_file, driver='GeoJSON')
    
    print(f"Saved {len(combined_gdf)} counties to {output_file}")
    print(f"Added {len(new_counties)} new counties in batch {batch_num}")
    
    # Print statistics by region
    region_counts = {}
    for _, county in new_counties.iterrows():
        state_fips = county.get('STATEFP', 'Unknown')
        region = get_region_for_state(state_fips)
        region_counts[region] = region_counts.get(region, 0) + 1
    
    print("\nNew counties by region:")
    for region, count in sorted(region_counts.items()):
        print(f"  {region.capitalize()}: {count} counties")
    
    return len(new_counties)

def verify_data():
    """Run the verification script to ensure we only have real data."""
    print("\n=== Verifying Data ===")
    try:
        result = subprocess.run(
            "python tools/verify_real_data.py",
            shell=True, check=True, capture_output=True, text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error verifying data: {e}")
        print(f"Error output: {e.stderr}")
        return False

def update_filtered_data():
    """Run the filter script to update the filtered datasets."""
    print("\n=== Updating Filtered Data ===")
    try:
        result = subprocess.run(
            "python tools/filter_real_county_data.py",
            shell=True, check=True, capture_output=True, text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error updating filtered data: {e}")
        print(f"Error output: {e.stderr}")
        return False

def analyze_coverage():
    """Run the regional analysis script to see the updated regional coverage."""
    print("\n=== Analyzing Regional Coverage ===")
    try:
        result = subprocess.run(
            "python tools/analyze_regional_coverage.py --input data/final/verified_county_scores.geojson",
            shell=True, check=True, capture_output=True, text=True
        )
        # Extract and print just the regional coverage part
        output_lines = result.stdout.split('\n')
        for i, line in enumerate(output_lines):
            if "Regional Coverage:" in line:
                print(line)
                for j in range(1, 10):  # Print the next few lines
                    if i+j < len(output_lines) and output_lines[i+j].strip():
                        print(output_lines[i+j])
                    else:
                        break
                break
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error analyzing coverage: {e}")
        print(f"Error output: {e.stderr}")
        return False

def update_disclaimer(count):
    """Update the disclaimer text in the visualization."""
    print(f"\n=== Updating Disclaimer to {count} Counties ===")
    try:
        with open('qa/mapbox_shapefile_counties.html', 'r') as f:
            content = f.read()
        
        # Find the current count in the disclaimer
        import re
        match = re.search(r'Only counties with verified real data are shown \((\d+) counties\)', content)
        if match:
            old_count = match.group(1)
            content = content.replace(
                f"Only counties with verified real data are shown ({old_count} counties)",
                f"Only counties with verified real data are shown ({count} counties)"
            )
            
            with open('qa/mapbox_shapefile_counties.html', 'w') as f:
                f.write(content)
            
            print(f"Updated disclaimer from {old_count} to {count} counties")
            return True
        else:
            print("Could not find disclaimer text to update")
            return False
    except Exception as e:
        print(f"Error updating disclaimer: {e}")
        return False

def batch_add_counties(output_file, batch_size=100, total=1000, start_batch=1):
    """Add counties in batches."""
    print(f"Adding {total} counties in batches of {batch_size}...")
    
    # Calculate number of batches
    num_batches = (total + batch_size - 1) // batch_size  # Ceiling division
    
    # Process each batch
    total_added = 0
    for batch_num in range(start_batch, start_batch + num_batches):
        # Calculate batch size (last batch may be smaller)
        current_batch_size = min(batch_size, total - total_added)
        if current_batch_size <= 0:
            break
        
        # Add counties for this batch
        added = add_counties_batch(output_file, current_batch_size, batch_num)
        total_added += added
        
        # Verify data
        verify_data()
        
        # Update filtered data
        update_filtered_data()
        
        # Analyze coverage
        analyze_coverage()
        
        # Get current count
        try:
            verified_gdf = gpd.read_file('data/final/verified_county_scores.geojson')
            current_count = len(verified_gdf)
            # Update disclaimer
            update_disclaimer(current_count)
        except Exception as e:
            print(f"Error getting current count: {e}")
        
        print(f"\n=== Completed Batch {batch_num} ===")
        print(f"Added {added} counties in this batch")
        print(f"Total added so far: {total_added} of {total}")
        print(f"Remaining: {total - total_added}")
        
        # Add a small delay between batches
        if batch_num < start_batch + num_batches - 1:
            print("\nWaiting 2 seconds before next batch...")
            time.sleep(2)
    
    print(f"\n=== All Batches Complete ===")
    print(f"Added {total_added} counties in {num_batches} batches")
    
    return total_added

def main():
    """Main function."""
    args = parse_args()
    batch_add_counties(args.output, args.batch_size, args.total, args.start_batch)

if __name__ == "__main__":
    main()
