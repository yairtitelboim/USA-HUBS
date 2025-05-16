#!/bin/bash

# County Data Analysis Shell Script
# This script runs both analysis tools

# Exit on error
set -e

echo "===== Running County Data Analysis Tools ====="

# Make sure Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 to run these scripts."
    exit 1
fi

# Check if required Python libraries are installed
echo "Checking for required Python libraries..."
python3 -c "import pandas, numpy, matplotlib, seaborn, scipy" 2>/dev/null || {
    echo "Missing required Python libraries."
    echo "Please install them with:"
    echo "pip install pandas numpy matplotlib seaborn scipy"
    exit 1
}

# Check if data file exists
if [ ! -f "../data/final/county_scores.geojson" ]; then
    echo "Data file not found: ../data/final/county_scores.geojson"
    echo "Please ensure the path is correct or update the script paths."
    exit 1
fi

echo "Step 1: Running main data validation and analysis script..."
python3 county_data_validation.py

echo "Step 2: Running high overlap analysis script..."
python3 high_overlap_analysis.py

echo "Analysis complete!"
echo "Results can be found in the analysis_results and overlap_analysis directories." 