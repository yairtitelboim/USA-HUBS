#!/usr/bin/env python3
"""
Create Test Data for County Analysis

This script generates a synthetic GeoJSON file with sample county data, including
obsolescence_score and growth_potential_score properties for testing the analysis scripts.
"""

import json
import os
import random
import numpy as np
from datetime import datetime

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Define directories
OUTPUT_DIR = "../data/final"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define parameters
NUM_COUNTIES = 100  # Number of synthetic counties
CORRELATION = 0.3   # Correlation between obsolescence and growth (-1 to 1)

def create_correlated_data(n, r):
    """Create two sets of correlated random data
    
    Args:
        n: Number of data points to generate
        r: Correlation coefficient (-1 to 1)
    
    Returns:
        Tuple of two numpy arrays with the specified correlation
    """
    # Generate random data
    x = np.random.random(n)
    
    # Create correlated data
    # We'll generate random noise and combine it with x to get the desired correlation
    noise = np.random.random(n)
    
    # Combine x and noise to achieve correlation r
    # This formula produces a variable that has correlation r with x
    y = r * x + np.sqrt(1 - r**2) * noise
    
    # Ensure values are between 0 and 1
    y = np.clip(y, 0, 1)
    
    return x, y

def create_county_geojson():
    """Create a GeoJSON file with synthetic county data"""
    
    # Generate correlated obsolescence and growth scores
    obsolescence_scores, growth_scores = create_correlated_data(NUM_COUNTIES, CORRELATION)
    
    # Create county features
    features = []
    for i in range(NUM_COUNTIES):
        # Create a simple square polygon for each county
        # (This is just for structure, not for actual visualization)
        x_base = random.uniform(-120, -70)  # Random longitude in US
        y_base = random.uniform(25, 45)     # Random latitude in US
        
        # Create a small square polygon
        coords = [
            [x_base, y_base],
            [x_base + 0.5, y_base],
            [x_base + 0.5, y_base + 0.5],
            [x_base, y_base + 0.5],
            [x_base, y_base]
        ]
        
        # Create county properties
        county_name = f"Sample County {i+1}"
        state_fp = str(random.randint(1, 50)).zfill(2)  # State FIPS code
        county_fp = str(random.randint(1, 999)).zfill(3)  # County FIPS code
        geoid = f"{state_fp}{county_fp}"
        
        # Create a feature with properties
        feature = {
            "type": "Feature",
            "properties": {
                "GEOID": geoid,
                "NAME": county_name,
                "STATEFP": state_fp,
                "COUNTYFP": county_fp,
                "obsolescence_score": float(obsolescence_scores[i]),
                "growth_potential_score": float(growth_scores[i]),
                "confidence": random.uniform(0.7, 0.95),
                "tile_count": random.randint(5, 20),
                "data_source": "synthetic",
                "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }
        
        features.append(feature)
    
    # Create the GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Write to file
    output_file = os.path.join(OUTPUT_DIR, "county_scores.geojson")
    with open(output_file, 'w') as f:
        json.dump(geojson, f, indent=2)
    
    print(f"Created synthetic test data file with {NUM_COUNTIES} counties at: {output_file}")
    
    # Write some statistics
    obs_mean = np.mean(obsolescence_scores)
    growth_mean = np.mean(growth_scores)
    actual_corr = np.corrcoef(obsolescence_scores, growth_scores)[0, 1]
    
    print(f"Statistics:")
    print(f"  Mean obsolescence score: {obs_mean:.4f}")
    print(f"  Mean growth potential score: {growth_mean:.4f}")
    print(f"  Correlation: {actual_corr:.4f} (target was {CORRELATION})")
    
    # Also create a separate special test case with high values of both
    # Create 20 counties with high values on both metrics
    create_special_test_cases()

def create_special_test_cases():
    """Create additional test counties with specific patterns"""
    
    # Load the existing data
    output_file = os.path.join(OUTPUT_DIR, "county_scores.geojson")
    with open(output_file, 'r') as f:
        geojson = json.load(f)
    
    features = geojson['features']
    
    # Get the highest ID used
    max_id = max([int(f['properties']['GEOID']) for f in features])
    
    # Create 10 counties with both high obsolescence and high growth
    for i in range(10):
        # Random but high values for both scores
        obs_score = random.uniform(0.7, 0.95)
        growth_score = random.uniform(0.7, 0.95)
        
        # Create county properties
        county_name = f"High-High County {i+1}"
        geoid = str(max_id + i + 1)
        state_fp = str(random.randint(1, 50)).zfill(2)
        
        # Random location
        x_base = random.uniform(-120, -70)
        y_base = random.uniform(25, 45)
        
        # Create a small square polygon
        coords = [
            [x_base, y_base],
            [x_base + 0.5, y_base],
            [x_base + 0.5, y_base + 0.5],
            [x_base, y_base + 0.5],
            [x_base, y_base]
        ]
        
        # Create a feature
        feature = {
            "type": "Feature",
            "properties": {
                "GEOID": geoid,
                "NAME": county_name,
                "STATEFP": state_fp,
                "COUNTYFP": "999",
                "obsolescence_score": obs_score,
                "growth_potential_score": growth_score,
                "confidence": 0.95,
                "tile_count": 20,
                "data_source": "synthetic_special",
                "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }
        
        features.append(feature)
    
    # Write updated GeoJSON to file
    with open(output_file, 'w') as f:
        json.dump(geojson, f, indent=2)
    
    print(f"Added 10 special test counties with high values on both metrics")

if __name__ == "__main__":
    create_county_geojson() 