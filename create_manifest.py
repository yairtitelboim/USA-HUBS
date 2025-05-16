#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Create a manifest of exported Sentinel-2 files and download samples.

This script creates a manifest of exported Sentinel-2 files in a Google Cloud Storage bucket,
and optionally downloads a sample of files for quality control.
"""

import os
import argparse
import subprocess
import random
import json
from datetime import datetime
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

def run_gsutil_command(command):
    """
    Run a gsutil command and return the output.

    Args:
        command: gsutil command to run

    Returns:
        Command output as a string
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error message: {e.stderr}")
        return None

def list_files_in_bucket(bucket, prefix=None, start_date=None, end_date=None):
    """
    List files in a Google Cloud Storage bucket.

    Args:
        bucket: Google Cloud Storage bucket name
        prefix: Optional prefix to filter files
        start_date: Optional start date to filter files (format: YYYY-MM-DD)
        end_date: Optional end date to filter files (format: YYYY-MM-DD)

    Returns:
        List of file paths
    """
    command = f"gsutil ls gs://{bucket}"
    if prefix:
        command += f"/{prefix}"

    # Add wildcard to list all files
    if not command.endswith("*"):
        command += "/**/*.tif"

    output = run_gsutil_command(command)
    if not output:
        return []

    files = output.strip().split('\n')

    # Filter by date if specified
    if start_date or end_date:
        filtered_files = []

        for file_path in files:
            # Extract date from file path
            # Format: gs://bucket/YYYY-MM/tile_id/file.tif
            parts = file_path.split('/')
            if len(parts) < 4:
                continue

            # Get the date part (YYYY-MM)
            file_date = parts[3]

            # Check if it's a valid date format
            if not file_date.startswith('20') or len(file_date.split('-')) < 2:
                continue

            # Filter by start date
            if start_date and file_date < start_date:
                continue

            # Filter by end date
            if end_date and file_date > end_date:
                continue

            filtered_files.append(file_path)

        return filtered_files
    else:
        return files

def create_manifest(files, output_path):
    """
    Create a manifest file from a list of file paths.

    Args:
        files: List of file paths
        output_path: Path to save the manifest

    Returns:
        Path to the saved manifest
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write files to manifest
    with open(output_path, 'w') as f:
        for file_path in files:
            f.write(f"{file_path}\n")

    return output_path

def download_samples(files, output_dir, sample_size=10):
    """
    Download a sample of files from a list.

    Args:
        files: List of file paths
        output_dir: Directory to save downloaded files
        sample_size: Number of files to download

    Returns:
        List of downloaded file paths
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Sample files
    if len(files) <= sample_size:
        sample = files
    else:
        sample = random.sample(files, sample_size)

    # Download each file
    downloaded_files = []
    for i, file_path in enumerate(sample):
        print(f"Downloading file {i+1}/{len(sample)}: {file_path}")

        # Extract file name from path
        file_name = os.path.basename(file_path)

        # Create local path
        local_path = os.path.join(output_dir, file_name)

        # Download file
        command = f"gsutil cp {file_path} {local_path}"
        run_gsutil_command(command)

        if os.path.exists(local_path):
            downloaded_files.append(local_path)

    return downloaded_files

def analyze_sample(file_path):
    """
    Analyze a sample GeoTIFF file.

    Args:
        file_path: Path to the GeoTIFF file

    Returns:
        Dictionary with analysis results
    """
    with rasterio.open(file_path) as src:
        # Read data
        data = src.read()

        # Get metadata
        metadata = src.meta

        # Calculate cloud cover (percentage of masked pixels)
        valid_pixels = np.sum(data[0] != 0)
        total_pixels = data[0].size
        valid_percentage = (valid_pixels / total_pixels) * 100
        cloud_cover = 100 - valid_percentage

        # Calculate statistics for each band
        band_stats = []
        for i in range(data.shape[0]):
            # Mask out nodata values
            masked_data = data[i][data[i] != 0]

            if masked_data.size > 0:
                stats = {
                    'min': float(np.min(masked_data)),
                    'max': float(np.max(masked_data)),
                    'mean': float(np.mean(masked_data)),
                    'std': float(np.std(masked_data))
                }
            else:
                stats = {
                    'min': None,
                    'max': None,
                    'mean': None,
                    'std': None
                }

            band_stats.append(stats)

        # Create analysis results
        results = {
            'file_path': file_path,
            'shape': data.shape,
            'crs': str(src.crs),
            'transform': str(src.transform),
            'cloud_cover': cloud_cover,
            'valid_percentage': valid_percentage,
            'band_stats': band_stats
        }

        return results

def create_mosaic(files, output_path, grid_size=(5, 5)):
    """
    Create a mosaic of GeoTIFF files.

    Args:
        files: List of GeoTIFF file paths
        output_path: Path to save the mosaic
        grid_size: Size of the mosaic grid (rows, columns)

    Returns:
        Path to the saved mosaic
    """
    # Limit the number of files to the grid size
    max_files = grid_size[0] * grid_size[1]
    if len(files) > max_files:
        files = files[:max_files]

    # Create figure
    fig, axes = plt.subplots(grid_size[0], grid_size[1], figsize=(15, 15))
    axes = axes.flatten()

    # Create a normalization for RGB values
    norm = Normalize(vmin=0, vmax=0.3)

    # Plot each file
    for i, file_path in enumerate(files):
        if i >= len(axes):
            break

        try:
            with rasterio.open(file_path) as src:
                # Read RGB bands
                rgb = src.read([1, 2, 3])

                # Transpose to (height, width, channels)
                rgb = np.transpose(rgb, (1, 2, 0))

                # Normalize values
                rgb = norm(rgb)

                # Clip values to [0, 1]
                rgb = np.clip(rgb, 0, 1)

                # Plot
                axes[i].imshow(rgb)
                axes[i].set_title(os.path.basename(file_path), fontsize=8)
                axes[i].axis('off')
        except Exception as e:
            print(f"Error plotting {file_path}: {e}")
            axes[i].text(0.5, 0.5, f"Error: {str(e)}", ha='center', va='center', fontsize=8)
            axes[i].axis('off')

    # Hide unused axes
    for i in range(len(files), len(axes)):
        axes[i].axis('off')

    # Adjust layout
    plt.tight_layout()

    # Save figure
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return output_path

def main():
    """Main function to create a manifest and download samples."""
    parser = argparse.ArgumentParser(description="Create a manifest of exported Sentinel-2 files")

    # Required arguments
    parser.add_argument("bucket", help="Google Cloud Storage bucket name")

    # Optional arguments
    parser.add_argument("--prefix", help="Prefix to filter files (e.g., '2024-*')")
    parser.add_argument("--start-date", help="Start date to filter files (format: YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date to filter files (format: YYYY-MM-DD)")
    parser.add_argument("--manifest", default="manifests/manifest.txt",
                        help="Path to save the manifest (default: manifests/manifest.txt)")
    parser.add_argument("--download", action="store_true",
                        help="Download a sample of files")
    parser.add_argument("--output-dir", default="data/raw",
                        help="Directory to save downloaded files (default: data/raw)")
    parser.add_argument("--sample-size", type=int, default=10,
                        help="Number of files to download (default: 10)")
    parser.add_argument("--analyze", action="store_true",
                        help="Analyze downloaded samples")
    parser.add_argument("--report", default="qa/sample_analysis.json",
                        help="Path to save analysis report (default: qa/sample_analysis.json)")
    parser.add_argument("--mosaic", action="store_true",
                        help="Create a mosaic of downloaded samples")
    parser.add_argument("--mosaic-output", default="qa/mosaic.png",
                        help="Path to save the mosaic (default: qa/mosaic.png)")
    parser.add_argument("--grid-size", type=int, nargs=2, default=[5, 5],
                        help="Size of the mosaic grid (rows columns) (default: 5 5)")

    args = parser.parse_args()

    # List files in bucket
    print(f"Listing files in gs://{args.bucket}...")
    files = list_files_in_bucket(
        args.bucket,
        args.prefix,
        args.start_date,
        args.end_date
    )
    print(f"Found {len(files)} files")

    # Create manifest
    if len(files) > 0:
        manifest_path = create_manifest(files, args.manifest)
        print(f"Created manifest with {len(files)} files: {manifest_path}")
    else:
        print("No files found, manifest not created")
        return

    # Download samples if requested
    downloaded_files = []
    if args.download:
        print(f"Downloading {args.sample_size} sample files to {args.output_dir}...")
        downloaded_files = download_samples(files, args.output_dir, args.sample_size)
        print(f"Downloaded {len(downloaded_files)} files")

    # Analyze samples if requested
    if args.analyze and downloaded_files:
        print("Analyzing downloaded samples...")

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(args.report), exist_ok=True)

        # Analyze each file
        analysis_results = []
        for file_path in downloaded_files:
            print(f"Analyzing {file_path}...")
            results = analyze_sample(file_path)
            analysis_results.append(results)

        # Save analysis report
        report = {
            'timestamp': datetime.now().isoformat(),
            'sample_size': len(downloaded_files),
            'results': analysis_results
        }

        with open(args.report, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Saved analysis report to {args.report}")

        # Print summary
        cloud_cover_values = [result['cloud_cover'] for result in analysis_results]
        if cloud_cover_values:
            avg_cloud_cover = sum(cloud_cover_values) / len(cloud_cover_values)
            print(f"Average cloud cover: {avg_cloud_cover:.2f}%")

            # Flag tiles with high cloud cover
            high_cloud_cover = [result['file_path'] for result in analysis_results if result['cloud_cover'] > 50]
            if high_cloud_cover:
                print(f"Warning: {len(high_cloud_cover)} tiles have > 50% cloud cover:")
                for path in high_cloud_cover:
                    print(f"  - {path}")

    # Create mosaic if requested
    if args.mosaic and downloaded_files:
        print("Creating mosaic of downloaded samples...")

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(args.mosaic_output), exist_ok=True)

        # Create mosaic
        mosaic_path = create_mosaic(downloaded_files, args.mosaic_output, tuple(args.grid_size))
        print(f"Saved mosaic to {mosaic_path}")

if __name__ == "__main__":
    main()
