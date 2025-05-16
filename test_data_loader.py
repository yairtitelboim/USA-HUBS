#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for the Sentinel-2 data loader.

This script tests the Sentinel2TileDataset class by loading a sample of tiles
and benchmarking the loading speed.
"""

import os
import argparse
import matplotlib.pyplot as plt
import numpy as np
from loghub.data_loader import Sentinel2TileDataset, benchmark_loading_speed

def plot_tile(data, metadata, output_path=None):
    """
    Plot a Sentinel-2 tile.
    
    Args:
        data: Tile data as a numpy array
        metadata: Tile metadata
        output_path: Path to save the plot
        
    Returns:
        Path to the saved plot if output_path is provided
    """
    # Create figure
    plt.figure(figsize=(10, 8))
    
    # Plot RGB bands
    rgb = np.transpose(data, (1, 2, 0))
    plt.imshow(rgb)
    
    # Add title
    plt.title(os.path.basename(metadata['file_path']))
    
    # Add metadata
    plt.figtext(0.1, 0.01, f"CRS: {metadata.get('crs', 'N/A')}", fontsize=8)
    plt.figtext(0.5, 0.01, f"Bounds: {metadata.get('bounds', 'N/A')}", fontsize=8)
    
    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        return output_path
    else:
        plt.show()
        return None

def main():
    """Main function to test the data loader."""
    parser = argparse.ArgumentParser(description="Test the Sentinel-2 data loader")
    
    # Data source options
    data_group = parser.add_mutually_exclusive_group(required=True)
    data_group.add_argument("--manifest", help="Path to the manifest file")
    data_group.add_argument("--data-dir", help="Directory containing the tile files")
    
    # Test options
    parser.add_argument("--sample-size", type=int, default=5,
                        help="Number of samples to load (default: 5)")
    parser.add_argument("--batch-size", type=int, default=1,
                        help="Batch size for loading (default: 1)")
    parser.add_argument("--output-dir", default="qa/test_plots",
                        help="Directory to save test plots (default: qa/test_plots)")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
    
    # Create dataset
    if args.manifest:
        dataset = Sentinel2TileDataset(manifest_path=args.manifest, data_dir=args.data_dir)
    else:
        dataset = Sentinel2TileDataset(data_dir=args.data_dir)
    
    # Print dataset info
    print(f"Dataset size: {len(dataset)} tiles")
    
    # Benchmark loading speed
    print("Benchmarking loading speed...")
    results = benchmark_loading_speed(dataset, num_samples=args.sample_size, batch_size=args.batch_size)
    
    print(f"Loaded {results['num_samples']} samples in {results['total_time']:.2f} seconds")
    print(f"Loading speed: {results['time_per_sample']:.4f} seconds per sample")
    print(f"Throughput: {results['samples_per_second']:.2f} samples per second")
    
    # Plot a few samples
    print("Plotting samples...")
    for i in range(min(args.sample_size, len(dataset))):
        data, metadata = dataset[i]
        
        # Skip if there was an error loading the tile
        if 'error' in metadata:
            print(f"Skipping tile {i} due to error: {metadata['error']}")
            continue
        
        # Plot the tile
        output_path = os.path.join(args.output_dir, f"tile_{i}.png")
        plot_tile(data, metadata, output_path)
        print(f"Saved plot to {output_path}")

if __name__ == "__main__":
    main()
