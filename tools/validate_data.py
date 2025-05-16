#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Validate data quality for obsolescence scores.

This script checks the quality of obsolescence scores and other metrics
before they are used in the visualization pipeline.
"""

import os
import sys
import argparse
import json
import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path


def validate_geojson(geojson_path, required_fields=None, output_path=None):
    """
    Validate a GeoJSON file for data quality issues.

    Args:
        geojson_path: Path to the GeoJSON file
        required_fields: List of required fields to check
        output_path: Path to save the validation report

    Returns:
        Dictionary with validation results
    """
    print(f"Validating GeoJSON file: {geojson_path}")

    # Default required fields if not specified
    if required_fields is None:
        required_fields = ['GEOID', 'obsolescence_score', 'confidence', 'tile_count']

    # Check if file exists
    if not os.path.exists(geojson_path):
        return {
            'status': 'error',
            'message': f"File not found: {geojson_path}"
        }

    try:
        # Load GeoJSON file
        gdf = gpd.read_file(geojson_path)

        # Initialize validation results
        validation = {
            'status': 'success',
            'file_path': geojson_path,
            'feature_count': len(gdf),
            'fields': {},
            'missing_fields': [],
            'issues': []
        }

        # Check for required fields
        for field in required_fields:
            if field not in gdf.columns:
                validation['missing_fields'].append(field)
                validation['issues'].append(f"Missing required field: {field}")

        # If any required fields are missing, return early
        if validation['missing_fields']:
            validation['status'] = 'warning'

            # Save validation report if output path is provided
            if output_path:
                save_validation_report(validation, output_path)

            return validation

        # Validate each field
        for field in required_fields:
            field_data = gdf[field]

            # Skip geometry field
            if field == 'geometry':
                continue

            # Check data type
            dtype = str(field_data.dtype)

            # Calculate statistics
            stats = {
                'dtype': dtype,
                'count': len(field_data),
                'null_count': field_data.isna().sum(),
                'null_percentage': round(field_data.isna().sum() / len(field_data) * 100, 2) if len(field_data) > 0 else 0
            }

            # Add numeric statistics if applicable
            if pd.api.types.is_numeric_dtype(field_data):
                non_null_data = field_data.dropna()

                if len(non_null_data) > 0:
                    stats.update({
                        'min': float(non_null_data.min()),
                        'max': float(non_null_data.max()),
                        'mean': float(non_null_data.mean()),
                        'median': float(non_null_data.median()),
                        'std': float(non_null_data.std()),
                        'zeros_count': int((non_null_data == 0).sum()),
                        'zeros_percentage': round((non_null_data == 0).sum() / len(non_null_data) * 100, 2) if len(non_null_data) > 0 else 0,
                        'negative_count': int((non_null_data < 0).sum()),
                        'negative_percentage': round((non_null_data < 0).sum() / len(non_null_data) * 100, 2) if len(non_null_data) > 0 else 0
                    })

                    # Check for potential issues
                    if stats['null_percentage'] > 5:
                        validation['issues'].append(f"High null percentage in {field}: {stats['null_percentage']}%")

                    if field == 'obsolescence_score':
                        if stats['min'] < 0:
                            validation['issues'].append(f"Negative values in {field}: {stats['negative_count']} values")

                        if stats['max'] > 1:
                            validation['issues'].append(f"{field} has values > 1: max = {stats['max']}")

                    if field == 'confidence':
                        if stats['min'] < 0:
                            validation['issues'].append(f"Negative values in {field}: {stats['negative_count']} values")

                        if stats['max'] > 1:
                            validation['issues'].append(f"{field} has values > 1: max = {stats['max']}")

                    if field == 'tile_count':
                        if stats['min'] < 0:
                            validation['issues'].append(f"Negative values in {field}: {stats['negative_count']} values")

            # Add field statistics to validation results
            validation['fields'][field] = stats

        # Update status based on issues
        if validation['issues']:
            validation['status'] = 'warning'

        # Save validation report if output path is provided
        if output_path:
            save_validation_report(validation, output_path)

        return validation

    except Exception as e:
        error_message = f"Error validating GeoJSON: {str(e)}"
        print(error_message)

        validation = {
            'status': 'error',
            'file_path': geojson_path,
            'message': error_message
        }

        # Save validation report if output path is provided
        if output_path:
            save_validation_report(validation, output_path)

        return validation


def validate_csv(csv_path, required_fields=None, output_path=None):
    """
    Validate a CSV file for data quality issues.

    Args:
        csv_path: Path to the CSV file
        required_fields: List of required fields to check
        output_path: Path to save the validation report

    Returns:
        Dictionary with validation results
    """
    print(f"Validating CSV file: {csv_path}")

    # Default required fields if not specified
    if required_fields is None:
        required_fields = ['tile_id', 'longitude', 'latitude', 'obsolescence_score', 'confidence']

    # Check if file exists
    if not os.path.exists(csv_path):
        return {
            'status': 'error',
            'message': f"File not found: {csv_path}"
        }

    try:
        # Load CSV file
        df = pd.read_csv(csv_path)

        # Initialize validation results
        validation = {
            'status': 'success',
            'file_path': csv_path,
            'row_count': len(df),
            'fields': {},
            'missing_fields': [],
            'issues': []
        }

        # Check for required fields
        for field in required_fields:
            if field not in df.columns:
                validation['missing_fields'].append(field)
                validation['issues'].append(f"Missing required field: {field}")

        # If any required fields are missing, return early
        if validation['missing_fields']:
            validation['status'] = 'warning'

            # Save validation report if output path is provided
            if output_path:
                save_validation_report(validation, output_path)

            return validation

        # Validate each field
        for field in required_fields:
            field_data = df[field]

            # Check data type
            dtype = str(field_data.dtype)

            # Calculate statistics
            stats = {
                'dtype': dtype,
                'count': len(field_data),
                'null_count': field_data.isna().sum(),
                'null_percentage': round(field_data.isna().sum() / len(field_data) * 100, 2) if len(field_data) > 0 else 0
            }

            # Add numeric statistics if applicable
            if pd.api.types.is_numeric_dtype(field_data):
                non_null_data = field_data.dropna()

                if len(non_null_data) > 0:
                    stats.update({
                        'min': float(non_null_data.min()),
                        'max': float(non_null_data.max()),
                        'mean': float(non_null_data.mean()),
                        'median': float(non_null_data.median()),
                        'std': float(non_null_data.std()),
                        'zeros_count': int((non_null_data == 0).sum()),
                        'zeros_percentage': round((non_null_data == 0).sum() / len(non_null_data) * 100, 2) if len(non_null_data) > 0 else 0,
                        'negative_count': int((non_null_data < 0).sum()),
                        'negative_percentage': round((non_null_data < 0).sum() / len(non_null_data) * 100, 2) if len(non_null_data) > 0 else 0
                    })

                    # Check for potential issues
                    if stats['null_percentage'] > 5:
                        validation['issues'].append(f"High null percentage in {field}: {stats['null_percentage']}%")

                    if field == 'obsolescence_score':
                        if stats['min'] < 0:
                            validation['issues'].append(f"Negative values in {field}: {stats['negative_count']} values")

                        if stats['max'] > 1:
                            validation['issues'].append(f"{field} has values > 1: max = {stats['max']}")

                    if field == 'confidence':
                        if stats['min'] < 0:
                            validation['issues'].append(f"Negative values in {field}: {stats['negative_count']} values")

                        if stats['max'] > 1:
                            validation['issues'].append(f"{field} has values > 1: max = {stats['max']}")

                    if field in ['longitude', 'latitude']:
                        # Check for valid coordinate ranges
                        if field == 'longitude' and (stats['min'] < -180 or stats['max'] > 180):
                            validation['issues'].append(f"Invalid {field} range: min = {stats['min']}, max = {stats['max']}")

                        if field == 'latitude' and (stats['min'] < -90 or stats['max'] > 90):
                            validation['issues'].append(f"Invalid {field} range: min = {stats['min']}, max = {stats['max']}")

            # Add field statistics to validation results
            validation['fields'][field] = stats

        # Update status based on issues
        if validation['issues']:
            validation['status'] = 'warning'

        # Save validation report if output path is provided
        if output_path:
            save_validation_report(validation, output_path)

        return validation

    except Exception as e:
        error_message = f"Error validating CSV: {str(e)}"
        print(error_message)

        validation = {
            'status': 'error',
            'file_path': csv_path,
            'message': error_message
        }

        # Save validation report if output path is provided
        if output_path:
            save_validation_report(validation, output_path)

        return validation


def save_validation_report(validation, output_path):
    """
    Save validation report to a JSON file.

    Args:
        validation: Validation results dictionary
        output_path: Path to save the validation report
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Convert numpy types to Python native types
    def convert_numpy_types(obj):
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        else:
            return obj

    # Convert numpy types in validation dictionary
    validation_converted = convert_numpy_types(validation)

    # Save validation report
    with open(output_path, 'w') as f:
        json.dump(validation_converted, f, indent=2)

    print(f"Validation report saved to: {output_path}")


def main():
    """Main function to validate data files."""
    parser = argparse.ArgumentParser(description="Validate data quality for obsolescence scores")

    # Required arguments
    parser.add_argument("--input", required=True,
                        help="Path to the input file (CSV or GeoJSON)")

    # Optional arguments
    parser.add_argument("--output", default=None,
                        help="Path to save the validation report (JSON)")
    parser.add_argument("--fields", nargs='+', default=None,
                        help="List of required fields to check")
    parser.add_argument("--type", choices=['auto', 'csv', 'geojson'], default='auto',
                        help="Type of input file (default: auto-detect)")

    args = parser.parse_args()

    # Determine file type
    file_type = args.type
    if file_type == 'auto':
        file_ext = os.path.splitext(args.input)[1].lower()
        if file_ext == '.csv':
            file_type = 'csv'
        elif file_ext in ['.geojson', '.json']:
            file_type = 'geojson'
        else:
            print(f"Error: Unable to determine file type for {args.input}")
            sys.exit(1)

    # Set default output path if not provided
    if args.output is None:
        input_path = Path(args.input)
        output_dir = input_path.parent / 'validation'
        os.makedirs(output_dir, exist_ok=True)
        args.output = output_dir / f"{input_path.stem}_validation.json"

    # Validate file
    if file_type == 'csv':
        validation = validate_csv(args.input, args.fields, args.output)
    else:  # geojson
        validation = validate_geojson(args.input, args.fields, args.output)

    # Print validation summary
    print("\nValidation Summary:")
    print(f"Status: {validation['status']}")

    if validation['status'] == 'error':
        print(f"Error: {validation.get('message', 'Unknown error')}")
        sys.exit(1)

    if 'feature_count' in validation:
        print(f"Feature Count: {validation['feature_count']}")
    elif 'row_count' in validation:
        print(f"Row Count: {validation['row_count']}")

    if validation.get('missing_fields'):
        print(f"Missing Fields: {', '.join(validation['missing_fields'])}")

    if validation.get('issues'):
        print("\nIssues Found:")
        for issue in validation['issues']:
            print(f"- {issue}")
    else:
        print("\nNo issues found.")

    print(f"\nDetailed validation report saved to: {args.output}")


if __name__ == "__main__":
    main()
