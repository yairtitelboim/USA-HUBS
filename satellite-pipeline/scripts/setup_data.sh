#!/bin/bash
#
# Setup Data for Satellite Pipeline
#
# This script sets up the data directory structure and copies or links
# county shapefiles from the main project.

set -e  # Exit on error

# Set paths
SCRIPT_DIR=$(dirname "$0")
PIPELINE_ROOT=$(dirname "$SCRIPT_DIR")
MAIN_PROJECT_ROOT="$PIPELINE_ROOT/.."
DATA_DIR="$PIPELINE_ROOT/data"
CONFIG_DIR="$PIPELINE_ROOT/config"

# Source project shapefile
SOURCE_SHAPEFILE_DIR="$MAIN_PROJECT_ROOT/data/tl_2024_us_county"

# Destination for shapefile
DEST_SHAPEFILE_DIR="$DATA_DIR/tl_2024_us_county"

# Create data directories if they don't exist
mkdir -p "$DATA_DIR/raw"
mkdir -p "$DATA_DIR/processed/time_series"
mkdir -p "$PIPELINE_ROOT/logs"

echo "Setting up satellite data pipeline directories..."

# Check if source shapefile exists
if [ -d "$SOURCE_SHAPEFILE_DIR" ]; then
    echo "Found county shapefile in main project"
    
    # Create symbolic link or copy files
    if [ ! -d "$DEST_SHAPEFILE_DIR" ]; then
        echo "Creating link to county shapefile..."
        
        # Option 1: Create symbolic link (preferred if on same filesystem)
        ln -sf "$SOURCE_SHAPEFILE_DIR" "$DEST_SHAPEFILE_DIR"
        
        # Option 2: Copy files (uncomment if symbolic link doesn't work)
        # mkdir -p "$DEST_SHAPEFILE_DIR"
        # cp -r "$SOURCE_SHAPEFILE_DIR/"* "$DEST_SHAPEFILE_DIR/"
    else
        echo "County shapefile directory already exists in pipeline data"
    fi
else
    echo "Warning: County shapefile not found in main project at $SOURCE_SHAPEFILE_DIR"
    echo "You need to manually copy the county shapefile to $DEST_SHAPEFILE_DIR"
fi

# Setup credentials file if it doesn't exist
if [ ! -f "$CONFIG_DIR/gee_credentials.json" ] && [ -f "$CONFIG_DIR/gee_credentials.example.json" ]; then
    echo "Creating credentials file from example..."
    cp "$CONFIG_DIR/gee_credentials.example.json" "$CONFIG_DIR/gee_credentials.json"
    echo "Please edit $CONFIG_DIR/gee_credentials.json with your actual credentials"
fi

echo "Setup complete!"
echo "Directory structure:"
find "$PIPELINE_ROOT" -type d | sort