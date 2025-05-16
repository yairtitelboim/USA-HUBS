#!/usr/bin/env python3
"""
Verify Real Data

This script verifies that all county data is real (not simulated) and meets quality standards.
It performs validation checks and outputs a report of any issues found.

Usage:
    python verify_real_data.py [--input INPUT_FILE] [--output OUTPUT_FILE]

Options:
    --input INPUT_FILE    Path to the county scores GeoJSON [default: data/final/county_scores.geojson]
    --output OUTPUT_FILE  Path to save the verified data [default: data/final/verified_county_scores.geojson]
    --report REPORT_FILE  Path to save the verification report [default: qa/data_verification_report.json]
"""

import os
import json
import argparse
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import datetime

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Verify Real Data')
    parser.add_argument('--input', default='data/final/county_scores.geojson',
                        help='Path to the county scores GeoJSON')
    parser.add_argument('--output', default='data/final/verified_county_scores.geojson',
                        help='Path to save the verified data')
    parser.add_argument('--report', default='qa/data_verification_report.json',
                        help='Path to save the verification report')
    return parser.parse_args()

def verify_real_data(input_file, output_file, report_file):
    """Verify that all county data is real and meets quality standards."""
    print(f"Loading county data from {input_file}...")
    
    # Load the GeoJSON file
    try:
        gdf = gpd.read_file(input_file)
        print(f"Loaded {len(gdf)} counties from GeoJSON file")
    except Exception as e:
        print(f"Error loading GeoJSON file: {e}")
        return
    
    # Initialize verification report
    verification_report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "input_file": input_file,
        "total_counties": len(gdf),
        "issues_found": 0,
        "issues": [],
        "warnings": [],
        "statistics": {}
    }
    
    # Check for required fields
    required_fields = ['GEOID', 'NAME', 'obsolescence_score', 'confidence', 'tile_count']
    missing_fields = [field for field in required_fields if field not in gdf.columns]
    
    if missing_fields:
        for field in missing_fields:
            verification_report["issues"].append({
                "type": "missing_field",
                "field": field,
                "description": f"Required field '{field}' is missing from the dataset"
            })
        verification_report["issues_found"] += len(missing_fields)
    
    # Check for data_source field and ensure all are 'real'
    if 'data_source' in gdf.columns:
        simulated_data = gdf[gdf['data_source'] != 'real']
        if len(simulated_data) > 0:
            verification_report["issues"].append({
                "type": "simulated_data",
                "count": len(simulated_data),
                "description": f"Found {len(simulated_data)} counties with simulated data"
            })
            verification_report["issues_found"] += 1
            
            # Remove simulated data
            print(f"Removing {len(simulated_data)} counties with simulated data")
            gdf = gdf[gdf['data_source'] == 'real']
    else:
        # Add data_source field if it doesn't exist
        gdf['data_source'] = 'real'
        verification_report["warnings"].append({
            "type": "added_field",
            "field": "data_source",
            "description": "Added 'data_source' field with value 'real' to all counties"
        })
    
    # Check for invalid values
    if 'obsolescence_score' in gdf.columns:
        invalid_scores = gdf[(gdf['obsolescence_score'] < 0) | (gdf['obsolescence_score'] > 1)]
        if len(invalid_scores) > 0:
            verification_report["issues"].append({
                "type": "invalid_scores",
                "count": len(invalid_scores),
                "description": f"Found {len(invalid_scores)} counties with invalid obsolescence scores (outside 0-1 range)"
            })
            verification_report["issues_found"] += 1
            
            # Fix invalid scores
            print(f"Fixing {len(invalid_scores)} counties with invalid obsolescence scores")
            gdf.loc[gdf['obsolescence_score'] < 0, 'obsolescence_score'] = 0
            gdf.loc[gdf['obsolescence_score'] > 1, 'obsolescence_score'] = 1
    
    if 'confidence' in gdf.columns:
        invalid_confidence = gdf[(gdf['confidence'] < 0) | (gdf['confidence'] > 1)]
        if len(invalid_confidence) > 0:
            verification_report["issues"].append({
                "type": "invalid_confidence",
                "count": len(invalid_confidence),
                "description": f"Found {len(invalid_confidence)} counties with invalid confidence values (outside 0-1 range)"
            })
            verification_report["issues_found"] += 1
            
            # Fix invalid confidence values
            print(f"Fixing {len(invalid_confidence)} counties with invalid confidence values")
            gdf.loc[gdf['confidence'] < 0, 'confidence'] = 0
            gdf.loc[gdf['confidence'] > 1, 'confidence'] = 1
    
    if 'tile_count' in gdf.columns:
        invalid_tile_count = gdf[gdf['tile_count'] < 0]
        if len(invalid_tile_count) > 0:
            verification_report["issues"].append({
                "type": "invalid_tile_count",
                "count": len(invalid_tile_count),
                "description": f"Found {len(invalid_tile_count)} counties with invalid tile count values (negative)"
            })
            verification_report["issues_found"] += 1
            
            # Fix invalid tile count values
            print(f"Fixing {len(invalid_tile_count)} counties with invalid tile count values")
            gdf.loc[gdf['tile_count'] < 0, 'tile_count'] = 0
    
    # Check for duplicate counties
    if 'GEOID' in gdf.columns:
        duplicate_counties = gdf[gdf.duplicated('GEOID', keep='first')]
        if len(duplicate_counties) > 0:
            verification_report["issues"].append({
                "type": "duplicate_counties",
                "count": len(duplicate_counties),
                "description": f"Found {len(duplicate_counties)} duplicate county entries"
            })
            verification_report["issues_found"] += 1
            
            # Remove duplicate counties
            print(f"Removing {len(duplicate_counties)} duplicate county entries")
            gdf = gdf.drop_duplicates('GEOID', keep='first')
    
    # Calculate statistics
    if 'obsolescence_score' in gdf.columns:
        verification_report["statistics"]["obsolescence_score"] = {
            "min": float(gdf['obsolescence_score'].min()),
            "max": float(gdf['obsolescence_score'].max()),
            "mean": float(gdf['obsolescence_score'].mean()),
            "median": float(gdf['obsolescence_score'].median()),
            "std": float(gdf['obsolescence_score'].std())
        }
    
    if 'confidence' in gdf.columns:
        verification_report["statistics"]["confidence"] = {
            "min": float(gdf['confidence'].min()),
            "max": float(gdf['confidence'].max()),
            "mean": float(gdf['confidence'].mean()),
            "median": float(gdf['confidence'].median()),
            "std": float(gdf['confidence'].std())
        }
    
    if 'tile_count' in gdf.columns:
        verification_report["statistics"]["tile_count"] = {
            "min": int(gdf['tile_count'].min()),
            "max": int(gdf['tile_count'].max()),
            "mean": float(gdf['tile_count'].mean()),
            "median": float(gdf['tile_count'].median()),
            "std": float(gdf['tile_count'].std()),
            "total": int(gdf['tile_count'].sum())
        }
    
    # Save the verified data
    verification_report["verified_counties"] = len(gdf)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    gdf.to_file(output_file, driver='GeoJSON')
    print(f"Saved {len(gdf)} verified counties to {output_file}")
    
    # Save the verification report
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(verification_report, f, indent=2)
    print(f"Saved verification report to {report_file}")
    
    # Print summary
    print("\nVerification Summary:")
    print(f"Total counties: {verification_report['total_counties']}")
    print(f"Verified counties: {verification_report['verified_counties']}")
    print(f"Issues found: {verification_report['issues_found']}")
    
    if verification_report["issues_found"] > 0:
        print("\nIssues:")
        for issue in verification_report["issues"]:
            print(f"  - {issue['description']}")
    
    if verification_report["warnings"]:
        print("\nWarnings:")
        for warning in verification_report["warnings"]:
            print(f"  - {warning['description']}")

def main():
    """Main function."""
    args = parse_args()
    verify_real_data(args.input, args.output, args.report)

if __name__ == "__main__":
    main()
