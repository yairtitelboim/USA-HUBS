#!/bin/bash

# Run Deck.gl prototype pipeline
# This script validates the data, opens the Deck.gl prototype in a browser,
# and generates a high-resolution PNG export

# Activate the Python environment
source loghub_env/bin/activate

# Set variables
GEOJSON_PATH="data/final/county_scores.geojson"
HTML_PATH="qa/deck_gl_prototype.html"
EXPORT_DIR="qa/exports"
VALIDATION_DIR="data/validation"

# Create directories if they don't exist
mkdir -p "$EXPORT_DIR"
mkdir -p "$VALIDATION_DIR"

# Step 1: Validate the GeoJSON data
echo "=========================================="
echo "Validating GeoJSON data..."
echo "=========================================="
python tools/validate_data.py \
  --input "$GEOJSON_PATH" \
  --output "$VALIDATION_DIR/county_scores_validation.json" \
  --type geojson

# Check if validation was successful
if [ $? -ne 0 ]; then
  echo "Error: Data validation failed. Please check the validation report."
  exit 1
fi

# Step 2: Open the Deck.gl prototype in a browser
echo "=========================================="
echo "Opening Deck.gl prototype in browser..."
echo "=========================================="
python -m http.server 8000 &
SERVER_PID=$!

# Wait for the server to start
sleep 2

# Open the browser
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  open "http://localhost:8000/$HTML_PATH"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  # Linux
  xdg-open "http://localhost:8000/$HTML_PATH"
else
  # Windows or other
  echo "Please open the following URL in your browser:"
  echo "http://localhost:8000/$HTML_PATH"
fi

# Step 3: Generate high-resolution PNG export
echo "=========================================="
echo "Generating high-resolution PNG export..."
echo "=========================================="
python tools/generate_deckgl_export.py \
  --html "$HTML_PATH" \
  --output-dir "$EXPORT_DIR" \
  --width 3840 \
  --height 2160 \
  --wait-time 10

# Check if export was successful
if [ $? -ne 0 ]; then
  echo "Warning: High-resolution export failed. You can still use the browser's export functionality."
fi

# Ask the user if they want to keep the server running
read -p "Do you want to keep the server running? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  # Stop the server
  kill $SERVER_PID
  echo "Server stopped."
else
  echo "Server is still running on http://localhost:8000"
  echo "Press Ctrl+C to stop the server when you're done."
  wait $SERVER_PID
fi

echo "Done!"
