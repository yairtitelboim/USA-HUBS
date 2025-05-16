#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Data loader for Sentinel-2 tiles.

This module provides utilities to load Sentinel-2 tiles from GeoTIFF files.
"""

import os
import glob
import time
import numpy as np
import rasterio
from torch.utils.data import Dataset, DataLoader

class Sentinel2TileDataset(Dataset):
    """
    Dataset for Sentinel-2 tiles.
    
    This dataset loads Sentinel-2 tiles from GeoTIFF files.
    """
    
    def __init__(self, manifest_path=None, data_dir=None, transform=None, 
                 bands=None, normalize=True):
        """
        Initialize the dataset.
        
        Args:
            manifest_path: Path to the manifest file listing all tile paths
            data_dir: Directory containing the tile files (alternative to manifest_path)
            transform: Optional transform to apply to the data
            bands: List of band indices to load (default: RGB bands [0, 1, 2])
            normalize: Whether to normalize the data to [0, 1]
        """
        self.transform = transform
        self.bands = bands if bands is not None else [0, 1, 2]  # Default to RGB
        self.normalize = normalize
        
        # Load file paths
        self.file_paths = []
        
        if manifest_path:
            # Load paths from manifest
            with open(manifest_path, 'r') as f:
                paths = f.read().strip().split('\n')
            
            # Filter out empty lines
            self.file_paths = [path for path in paths if path]
            
            # Check if paths are local or remote
            if self.file_paths and self.file_paths[0].startswith('gs://'):
                # Convert remote paths to local paths if data_dir is provided
                if data_dir:
                    self.file_paths = [self._gs_to_local(path, data_dir) for path in self.file_paths]
                else:
                    raise ValueError("data_dir must be provided when using remote paths in manifest")
        
        elif data_dir:
            # Find all GeoTIFF files in the directory
            self.file_paths = glob.glob(os.path.join(data_dir, '**', '*.tif'), recursive=True)
        
        else:
            raise ValueError("Either manifest_path or data_dir must be provided")
        
        # Sort file paths for reproducibility
        self.file_paths.sort()
        
        print(f"Loaded {len(self.file_paths)} tile paths")
    
    def _gs_to_local(self, gs_path, data_dir):
        """
        Convert a Google Cloud Storage path to a local path.
        
        Args:
            gs_path: Google Cloud Storage path
            data_dir: Local data directory
            
        Returns:
            Local file path
        """
        # Extract the relative path from the GCS path
        # Format: gs://bucket/path/to/file.tif
        parts = gs_path.split('/')
        
        # Skip the bucket name and join the rest
        relative_path = '/'.join(parts[3:])
        
        # Join with the local data directory
        local_path = os.path.join(data_dir, relative_path)
        
        return local_path
    
    def __len__(self):
        """Get the number of tiles in the dataset."""
        return len(self.file_paths)
    
    def __getitem__(self, idx):
        """
        Get a tile from the dataset.
        
        Args:
            idx: Index of the tile
            
        Returns:
            Tile data as a numpy array
        """
        # Get file path
        file_path = self.file_paths[idx]
        
        # Load tile
        try:
            with rasterio.open(file_path) as src:
                # Read specified bands
                data = src.read(self.bands)
                
                # Get metadata
                metadata = {
                    'file_path': file_path,
                    'crs': str(src.crs),
                    'transform': src.transform,
                    'bounds': src.bounds
                }
                
                # Normalize if requested
                if self.normalize:
                    # Clip values to [0, 1] assuming reflectance values
                    data = np.clip(data, 0, 1)
                
                # Apply transform if provided
                if self.transform:
                    data = self.transform(data)
                
                return data, metadata
        
        except Exception as e:
            print(f"Error loading tile {file_path}: {e}")
            
            # Return a placeholder for failed loads
            data = np.zeros((len(self.bands), 256, 256), dtype=np.float32)
            metadata = {
                'file_path': file_path,
                'error': str(e)
            }
            
            return data, metadata

def load_tile(file_path, bands=None, normalize=True):
    """
    Load a single Sentinel-2 tile.
    
    Args:
        file_path: Path to the GeoTIFF file
        bands: List of band indices to load (default: RGB bands [0, 1, 2])
        normalize: Whether to normalize the data to [0, 1]
        
    Returns:
        Tile data as a numpy array and metadata
    """
    bands = bands if bands is not None else [0, 1, 2]  # Default to RGB
    
    try:
        with rasterio.open(file_path) as src:
            # Read specified bands
            data = src.read(bands)
            
            # Get metadata
            metadata = {
                'file_path': file_path,
                'crs': str(src.crs),
                'transform': src.transform,
                'bounds': src.bounds
            }
            
            # Normalize if requested
            if normalize:
                # Clip values to [0, 1] assuming reflectance values
                data = np.clip(data, 0, 1)
            
            return data, metadata
    
    except Exception as e:
        print(f"Error loading tile {file_path}: {e}")
        
        # Return a placeholder for failed loads
        data = np.zeros((len(bands), 256, 256), dtype=np.float32)
        metadata = {
            'file_path': file_path,
            'error': str(e)
        }
        
        return data, metadata

def benchmark_loading_speed(dataset, num_samples=100, batch_size=1):
    """
    Benchmark the loading speed of a dataset.
    
    Args:
        dataset: Dataset to benchmark
        num_samples: Number of samples to load
        batch_size: Batch size for loading
        
    Returns:
        Dictionary with benchmark results
    """
    # Create data loader
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    # Limit the number of samples
    num_samples = min(num_samples, len(dataset))
    
    # Benchmark loading speed
    start_time = time.time()
    
    # Load samples
    samples_loaded = 0
    for i, (data, _) in enumerate(loader):
        samples_loaded += len(data)
        if samples_loaded >= num_samples:
            break
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Calculate loading speed
    loading_speed = elapsed_time / samples_loaded
    
    # Create benchmark results
    results = {
        'num_samples': samples_loaded,
        'batch_size': batch_size,
        'total_time': elapsed_time,
        'time_per_sample': loading_speed,
        'samples_per_second': 1 / loading_speed
    }
    
    return results
