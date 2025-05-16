#!/usr/bin/env python3
"""
Audit County Coverage

This script analyzes the county_scores.geojson file to check how many counties
have valid scores and provides statistics about the data coverage.

Usage:
    python audit_county_coverage.py [--input INPUT_FILE] [--output OUTPUT_FILE]

Options:
    --input INPUT_FILE    Path to the county scores GeoJSON file [default: data/final/county_scores.geojson]
    --output OUTPUT_FILE  Path to save the audit results JSON [default: data/validation/county_coverage.json]
    --verbose             Print detailed information
"""

import os
import json
import argparse
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Audit county coverage in GeoJSON data')
    parser.add_argument('--input', default='data/final/county_scores.geojson',
                        help='Path to the county scores GeoJSON file')
    parser.add_argument('--output', default='data/validation/county_coverage.json',
                        help='Path to save the audit results JSON')
    parser.add_argument('--verbose', action='store_true',
                        help='Print detailed information')
    return parser.parse_args()

def audit_county_coverage(input_file, output_file, verbose=False):
    """Audit county coverage in the GeoJSON data."""
    print(f"Loading county data from {input_file}...")

    # Load the GeoJSON file
    try:
        gdf = gpd.read_file(input_file)
        print(f"Loaded {len(gdf)} counties from GeoJSON file")
    except Exception as e:
        print(f"Error loading GeoJSON file: {e}")
        return

    # Check for required columns
    required_columns = ['obsolescence_score', 'confidence', 'tile_count']
    missing_columns = [col for col in required_columns if col not in gdf.columns]
    if missing_columns:
        print(f"Warning: Missing required columns: {missing_columns}")

    # Basic statistics
    stats = {
        "total_counties": len(gdf),
        "counties_with_data": 0,
        "coverage_percentage": 0,
        "score_statistics": {},
        "confidence_statistics": {},
        "tile_count_statistics": {},
        "states_coverage": {},
        "missing_columns": missing_columns
    }

    # Check counties with valid scores
    if 'obsolescence_score' in gdf.columns:
        valid_scores = gdf[gdf['obsolescence_score'] > 0]
        stats["counties_with_data"] = len(valid_scores)
        stats["coverage_percentage"] = (len(valid_scores) / len(gdf)) * 100

        print(f"{len(valid_scores)} of {len(gdf)} counties have data "
              f"({stats['coverage_percentage']:.2f}%)")

        # Score statistics
        stats["score_statistics"] = {
            "min": float(valid_scores['obsolescence_score'].min()),
            "max": float(valid_scores['obsolescence_score'].max()),
            "mean": float(valid_scores['obsolescence_score'].mean()),
            "median": float(valid_scores['obsolescence_score'].median()),
            "std": float(valid_scores['obsolescence_score'].std())
        }

        print(f"Score range: {stats['score_statistics']['min']:.2f} to "
              f"{stats['score_statistics']['max']:.2f}")
        print(f"Mean score: {stats['score_statistics']['mean']:.2f}")

    # Check confidence values
    if 'confidence' in gdf.columns:
        valid_confidence = gdf[gdf['confidence'] > 0]
        stats["confidence_statistics"] = {
            "counties_with_confidence": len(valid_confidence),
            "min": float(valid_confidence['confidence'].min()),
            "max": float(valid_confidence['confidence'].max()),
            "mean": float(valid_confidence['confidence'].mean()),
            "median": float(valid_confidence['confidence'].median())
        }

        if verbose:
            print(f"Confidence range: {stats['confidence_statistics']['min']:.2f} to "
                  f"{stats['confidence_statistics']['max']:.2f}")

    # Check tile counts
    if 'tile_count' in gdf.columns:
        valid_tiles = gdf[gdf['tile_count'] > 0]
        stats["tile_count_statistics"] = {
            "counties_with_tiles": len(valid_tiles),
            "min": int(valid_tiles['tile_count'].min()),
            "max": int(valid_tiles['tile_count'].max()),
            "mean": float(valid_tiles['tile_count'].mean()),
            "total_tiles": int(valid_tiles['tile_count'].sum())
        }

        if verbose:
            print(f"Total tiles processed: {stats['tile_count_statistics']['total_tiles']}")

    # State coverage if STATE column exists
    if 'STATE' in gdf.columns:
        state_coverage = {}
        for state, group in gdf.groupby('STATE'):
            valid_in_state = group[group['obsolescence_score'] > 0]
            state_coverage[state] = {
                "total_counties": len(group),
                "counties_with_data": len(valid_in_state),
                "coverage_percentage": (len(valid_in_state) / len(group)) * 100 if len(group) > 0 else 0
            }

        stats["states_coverage"] = state_coverage

        if verbose:
            print("\nState Coverage:")
            for state, coverage in sorted(state_coverage.items(),
                                         key=lambda x: x[1]['coverage_percentage'],
                                         reverse=True):
                print(f"{state}: {coverage['counties_with_data']}/{coverage['total_counties']} "
                      f"({coverage['coverage_percentage']:.2f}%)")

    # Save the audit results
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"\nAudit results saved to {output_file}")

    # Generate a simple visualization if we have valid data
    if 'obsolescence_score' in gdf.columns and len(valid_scores) > 0:
        generate_coverage_visualization(gdf, os.path.dirname(output_file))

def generate_coverage_visualization(gdf, output_dir):
    """Generate a simple visualization of the county coverage."""
    try:
        # Create a figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))

        # Plot 1: Score distribution histogram
        gdf[gdf['obsolescence_score'] > 0]['obsolescence_score'].hist(
            bins=20, ax=ax1, color='skyblue', edgecolor='black')
        ax1.set_title('Distribution of Obsolescence Scores')
        ax1.set_xlabel('Obsolescence Score')
        ax1.set_ylabel('Number of Counties')

        # Plot 2: Coverage map (simple)
        gdf['has_data'] = gdf['obsolescence_score'] > 0
        gdf.plot(column='has_data', ax=ax2, legend=True,
                 cmap='RdYlGn')
        ax2.set_title('County Coverage Map')
        ax2.set_axis_off()

        # Save the figure
        output_path = os.path.join(output_dir, 'county_coverage_visualization.png')
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

        print(f"Coverage visualization saved to {output_path}")
    except Exception as e:
        print(f"Error generating visualization: {e}")

def main():
    """Main function."""
    args = parse_args()
    audit_county_coverage(args.input, args.output, args.verbose)

if __name__ == "__main__":
    main()
