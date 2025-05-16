#!/usr/bin/env python3
"""
Satellite Metrics Processor

This module processes raw satellite data to calculate growth potential and 
obsolescence scores for counties.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape, Point

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parents[2] / 'logs' / 'processor.log')
    ]
)
logger = logging.getLogger('metrics_processor')

class MetricsProcessor:
    """Processor for calculating county metrics from satellite data."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the metrics processor.
        
        Args:
            output_dir: Directory to save processed data
        """
        self.output_dir = output_dir or str(Path(__file__).parents[2] / 'data' / 'processed')
        
        # Create necessary directories
        os.makedirs(Path(__file__).parents[2] / 'logs', exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
    def calculate_obsolescence_score(self, sample_data: Dict) -> float:
        """
        Calculate the obsolescence score from satellite index samples.
        
        The obsolescence score measures the degree of abandonment or degradation
        of built-up areas. Higher values indicate more obsolescence.
        
        Args:
            sample_data: GeoJSON feature collection with satellite index samples
            
        Returns:
            Obsolescence score (0-1 range)
        """
        try:
            # Convert to GeoDataFrame for easier processing
            features = sample_data.get('features', [])
            if not features:
                logger.error("No features found in sample data")
                return None
                
            # Extract properties from features
            properties = [feature.get('properties', {}) for feature in features]
            
            # Create DataFrame
            df = pd.DataFrame(properties)
            
            # Basic validity check
            required_indices = ['NDVI', 'NDBI', 'UI']
            if not all(idx in df.columns for idx in required_indices):
                logger.error(f"Missing required indices in sample data: {required_indices}")
                return None
                
            # Using the approach from process_real_satellite_data.py:
            # Higher NDBI and lower NDVI indicate more obsolescence (more built-up, less vegetation)
            df['obsolescence'] = df['NDBI'] - df['NDVI'] 
            
            # Scale to 0-1 range
            df['obsolescence'] = (df['obsolescence'] + 1) / 2
            
            # Calculate the median to avoid outlier influence
            # Using 75th percentile to highlight areas with more severe obsolescence
            obsolescence_score = np.percentile(df['obsolescence'].dropna(), 75)
            
            # Normalize to 0-1 range
            normalized_score = np.clip(obsolescence_score, 0, 1)
            
            # Apply regional adjustment if metadata contains state information
            # These adjustments are based on the regional patterns from process_real_satellite_data.py
            region_adjustments = {
                'south': 0.2,
                'east': 0.1,
                'west': 0.15,
                'midwest': -0.05,
                'northeast': -0.1
            }
            
            # We could determine region based on state FIPS code if available in metadata
            # For now, just returning the normalized score without adjustment
            
            logger.info(f"Calculated obsolescence score: {normalized_score:.4f}")
            return normalized_score
            
        except Exception as e:
            logger.error(f"Error calculating obsolescence score: {e}")
            return None
            
    def calculate_growth_potential(self, sample_data: Dict) -> float:
        """
        Calculate the growth potential score from satellite index samples.
        
        The growth potential score measures the potential for economic and infrastructure
        development. Higher values indicate more growth potential.
        
        Args:
            sample_data: GeoJSON feature collection with satellite index samples
            
        Returns:
            Growth potential score (0-1 range)
        """
        try:
            # Convert to GeoDataFrame for easier processing
            features = sample_data.get('features', [])
            if not features:
                logger.error("No features found in sample data")
                return None
                
            # Extract properties from features
            properties = [feature.get('properties', {}) for feature in features]
            
            # Create DataFrame
            df = pd.DataFrame(properties)
            
            # Basic validity check
            required_indices = ['NDVI', 'NDBI', 'NDWI', 'MNDWI']
            if not all(idx in df.columns for idx in required_indices):
                logger.error(f"Missing required indices in sample data: {required_indices}")
                return None
                
            # Calculate components of growth potential
            # 1. Vegetation health (moderate NDVI)
            # Growth potential is highest at moderate vegetation levels
            veg_health = 1 - np.abs(df['NDVI'] - 0.5) * 2
            
            # 2. Moderate built-up areas (moderate NDBI)
            # Areas with some development but not saturated have highest potential
            built_up_potential = 1 - np.abs(df['NDBI'] - 0.3) * 2
            
            # 3. Water availability (NDWI/MNDWI)
            water_availability = np.maximum(df['NDWI'], df['MNDWI']).clip(0, 1)
            
            # Combine indicators: Growth potential is high when:
            # - Area has moderate vegetation (moderate NDVI)
            # - Has moderate built-up areas (moderate NDBI)
            # - Has water resources available (high NDWI/MNDWI)
            growth_values = (
                veg_health * 0.4 +          # Weight for vegetation health
                built_up_potential * 0.4 +  # Weight for built-up potential
                water_availability * 0.2    # Weight for water availability
            )
            
            # Calculate the median to avoid outlier influence
            # Using 75th percentile to highlight areas with more growth potential
            growth_score = np.percentile(growth_values, 75)
            
            # Normalize to 0-1 range
            normalized_score = np.clip(growth_score, 0, 1)
            
            logger.info(f"Calculated growth potential score: {normalized_score:.4f}")
            return normalized_score
            
        except Exception as e:
            logger.error(f"Error calculating growth potential score: {e}")
            return None
    
    def process_county_data(self, 
                           sample_file: str,
                           metadata_file: Optional[str] = None) -> Dict:
        """
        Process raw satellite data for a county to generate metrics.
        
        Args:
            sample_file: Path to the sample data GeoJSON file
            metadata_file: Path to the metadata JSON file
            
        Returns:
            Dictionary with processed metrics
        """
        try:
            logger.info(f"Processing county data from {sample_file}")
            
            # Load sample data
            with open(sample_file, 'r') as f:
                sample_data = json.load(f)
                
            # Load metadata if provided
            metadata = {}
            if metadata_file and os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                # Try to infer metadata file from sample file path
                inferred_metadata_file = os.path.join(
                    os.path.dirname(sample_file),
                    "metadata.json"
                )
                if os.path.exists(inferred_metadata_file):
                    with open(inferred_metadata_file, 'r') as f:
                        metadata = json.load(f)
            
            # Calculate metrics
            obsolescence_score = self.calculate_obsolescence_score(sample_data)
            growth_potential = self.calculate_growth_potential(sample_data)
            
            # Create results dictionary
            results = {
                "county_fips": metadata.get("county_fips", "unknown"),
                "county_name": metadata.get("county_name", "unknown"),
                "state_fips": metadata.get("state_fips", "unknown"),
                "collection_date": metadata.get("collection_timestamp", "unknown"),
                "metrics": {
                    "obsolescence_score": obsolescence_score,
                    "growth_potential_score": growth_potential,
                    "bivariate_score": obsolescence_score * growth_potential if obsolescence_score and growth_potential else None
                },
                "metadata": {
                    "start_date": metadata.get("start_date", "unknown"),
                    "end_date": metadata.get("end_date", "unknown"),
                    "image_count": metadata.get("image_count", 0)
                }
            }
            
            # Save processed results
            timestamp = metadata.get("collection_timestamp", "unknown")
            county_fips = metadata.get("county_fips", "unknown")
            
            output_file = os.path.join(
                self.output_dir,
                f"{county_fips}_{timestamp}_metrics.json"
            )
            
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
                
            logger.info(f"Saved processed metrics to {output_file}")
            return results
            
        except Exception as e:
            logger.error(f"Error processing county data: {e}")
            return None
            
    def process_bulk(self, sample_files: List[str]) -> Dict[str, Dict]:
        """
        Process multiple county data files.
        
        Args:
            sample_files: List of paths to sample data GeoJSON files
            
        Returns:
            Dictionary mapping county FIPS codes to processed metrics
        """
        results = {}
        
        for sample_file in sample_files:
            try:
                processed_data = self.process_county_data(sample_file)
                if processed_data:
                    county_fips = processed_data.get("county_fips", "unknown")
                    results[county_fips] = processed_data
            except Exception as e:
                logger.error(f"Error processing {sample_file}: {e}")
                
        return results


if __name__ == "__main__":
    # Simple test run
    import argparse
    import glob
    
    parser = argparse.ArgumentParser(description="Process satellite data for counties")
    parser.add_argument('--input', required=True, help='Path to sample data file or directory')
    parser.add_argument('--output-dir', help='Directory to save processed data')
    args = parser.parse_args()
    
    processor = MetricsProcessor(output_dir=args.output_dir)
    
    if os.path.isdir(args.input):
        # Process all sample files in the directory
        sample_files = glob.glob(os.path.join(args.input, "*", "*_samples.geojson"))
        results = processor.process_bulk(sample_files)
        print(f"Processed {len(results)} counties")
    else:
        # Process single file
        results = processor.process_county_data(args.input)
        if results:
            print(f"Successfully processed county {results['county_fips']}")
            print(f"Obsolescence Score: {results['metrics']['obsolescence_score']:.4f}")
            print(f"Growth Potential Score: {results['metrics']['growth_potential_score']:.4f}")
        else:
            print("Processing failed")