#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration settings for visualizations.

This module contains configuration settings for visualizations,
including paths, default values, and other settings.
"""

# Paths
COUNTY_SHAPEFILE = "/Users/yairtitelboim/Documents/Kernel/ALLAPPS/LOGhub/data/tl_2024_us_county/tl_2024_us_county.shp"
OUTPUT_DIR = "qa"
FINAL_DATA_DIR = "data/final"
COMBINED_GEOJSON = "data/final/county_scores.geojson"

# Regions
REGIONS = ["south", "west", "east"]

# Visualization settings
DEFAULT_HEIGHT_FIELD = "confidence"  # Options: "confidence", "tile_count"
USE_MOCK_DATA = True  # Set to False to use only real data

# Mock data settings
MOCK_DATA_SEED = 42  # Random seed for reproducibility

# South region mock data
SOUTH_SCORE_RANGE = (0.6, 0.9)  # Higher obsolescence scores
SOUTH_CONFIDENCE_RANGE = (0.7, 0.95)
SOUTH_TILE_COUNT_RANGE = (5, 20)

# West region mock data
WEST_SCORE_RANGE = (0.4, 0.7)  # Medium obsolescence scores
WEST_CONFIDENCE_RANGE = (0.7, 0.95)
WEST_TILE_COUNT_RANGE = (5, 20)

# East region mock data
EAST_SCORE_RANGE = (0.2, 0.5)  # Lower obsolescence scores
EAST_CONFIDENCE_RANGE = (0.7, 0.95)
EAST_TILE_COUNT_RANGE = (5, 20)

# Color settings
COLOR_RAMP = ['#2c7bb6', '#ffffbf', '#d7191c']  # Blue to yellow to red
