#!/usr/bin/env python3
"""
Analyze Regional Coverage

This script analyzes the regional coverage of county data and identifies
regions that need more data.

Usage:
    python analyze_regional_coverage.py [--input INPUT_FILE]

Options:
    --input INPUT_FILE    Path to the county scores GeoJSON [default: data/final/verified_county_scores.geojson]
    --output OUTPUT_FILE  Path to save the regional coverage report [default: qa/regional_coverage_report.json]
"""

import os
import json
import argparse
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze Regional Coverage')
    parser.add_argument('--input', default='data/final/verified_county_scores.geojson',
                        help='Path to the county scores GeoJSON')
    parser.add_argument('--output', default='qa/regional_coverage_report.json',
                        help='Path to save the regional coverage report')
    return parser.parse_args()

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

    return state_names.get(state_fips, f"Unknown ({state_fips})")

def analyze_regional_coverage(input_file, output_file):
    """Analyze the regional coverage of county data."""
    print(f"Loading county data from {input_file}...")

    # Load the GeoJSON file
    try:
        gdf = gpd.read_file(input_file)
        print(f"Loaded {len(gdf)} counties from GeoJSON file")
    except Exception as e:
        print(f"Error loading GeoJSON file: {e}")
        return

    # Add region and state name columns
    if 'STATEFP' in gdf.columns:
        gdf['region'] = gdf['STATEFP'].apply(get_region_for_state)
        gdf['state_name'] = gdf['STATEFP'].apply(get_state_name)
    else:
        print("Warning: STATEFP column not found, cannot determine regions")
        return

    # Count counties by region
    region_counts = gdf['region'].value_counts().to_dict()
    print("\nRegional Coverage:")
    for region, count in region_counts.items():
        print(f"{region.capitalize()}: {count} counties")

    # Count counties by state
    state_counts = gdf.groupby(['state_name', 'region']).size().reset_index(name='count')
    state_counts = state_counts.sort_values(['region', 'count'], ascending=[True, False])

    print("\nState Coverage:")
    for _, row in state_counts.iterrows():
        print(f"{row['state_name']} ({row['region'].capitalize()}): {row['count']} counties")

    # Calculate regional statistics
    regional_stats = gdf.groupby('region').agg({
        'obsolescence_score': ['min', 'max', 'mean', 'std'],
        'confidence': ['min', 'max', 'mean'],
        'tile_count': ['sum', 'mean']
    }).reset_index()

    # Flatten the column names
    regional_stats.columns = ['_'.join(col).strip('_') for col in regional_stats.columns.values]

    # Convert to dictionary for JSON serialization
    regional_stats_dict = regional_stats.to_dict(orient='records')

    # Create the report
    report = {
        "total_counties": len(gdf),
        "region_counts": region_counts,
        "state_counts": state_counts.to_dict(orient='records'),
        "regional_stats": regional_stats_dict
    }

    # Save the report
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved regional coverage report to {output_file}")

    # Create visualizations
    create_regional_visualizations(gdf, os.path.dirname(output_file))

def create_regional_visualizations(gdf, output_dir):
    """Create visualizations of regional coverage."""
    print("Creating regional visualizations...")

    # Create a figure for region counts
    plt.figure(figsize=(10, 6))
    region_counts = gdf['region'].value_counts().sort_values(ascending=False)

    # Create bar plot with matplotlib
    bars = plt.bar(region_counts.index, region_counts.values, color='skyblue')
    plt.title('County Count by Region')
    plt.xlabel('Region')
    plt.ylabel('Number of Counties')
    plt.xticks(rotation=45)

    # Add count labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                 f'{int(height)}', ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'region_counts.png'))
    plt.close()

    # Create a figure for regional score distributions using boxplot
    plt.figure(figsize=(12, 8))

    # Group data by region for boxplot
    regions = gdf['region'].unique()
    data = [gdf[gdf['region'] == region]['obsolescence_score'] for region in regions]

    # Create boxplot
    plt.boxplot(data, labels=regions)
    plt.title('Obsolescence Score Distribution by Region')
    plt.xlabel('Region')
    plt.ylabel('Obsolescence Score')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'region_scores.png'))
    plt.close()

    # Create a figure for state counts
    plt.figure(figsize=(14, 10))
    state_counts = gdf.groupby(['state_name', 'region']).size().reset_index(name='count')
    state_counts = state_counts.sort_values(['region', 'count'], ascending=[True, False])

    # Get unique states and their counts
    states = state_counts['state_name'].tolist()
    counts = state_counts['count'].tolist()
    regions = state_counts['region'].tolist()

    # Create a color map for regions
    unique_regions = list(set(regions))
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_regions)))
    region_colors = {region: colors[i] for i, region in enumerate(unique_regions)}

    # Create bar colors based on region
    bar_colors = [region_colors[region] for region in regions]

    # Create the bar plot
    bars = plt.bar(range(len(states)), counts, color=bar_colors)

    plt.title('County Count by State')
    plt.xlabel('State')
    plt.ylabel('Number of Counties')
    plt.xticks(range(len(states)), states, rotation=90)

    # Add count labels on top of bars
    for i, count in enumerate(counts):
        plt.text(i, count + 0.1, str(count), ha='center')

    # Create legend
    legend_handles = [plt.Rectangle((0,0),1,1, color=region_colors[region]) for region in unique_regions]
    plt.legend(legend_handles, unique_regions, title='Region')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'state_counts.png'))
    plt.close()

    print(f"Saved visualizations to {output_dir}")

def main():
    """Main function."""
    args = parse_args()
    analyze_regional_coverage(args.input, args.output)

if __name__ == "__main__":
    main()
