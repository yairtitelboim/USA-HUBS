#!/bin/bash

# Export high-resolution map from Deck.gl prototype
# This script starts a local web server and generates a high-resolution PNG export

# Activate the Python environment
source loghub_env/bin/activate

# Set variables
HTML_PATH="qa/deck_gl_prototype.html"
EXPORT_DIR="qa/exports"
PORT=8000

# Create export directory if it doesn't exist
mkdir -p "$EXPORT_DIR"

# Check if port is already in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "Port $PORT is already in use. Please close the application using this port and try again."
    exit 1
fi

# Start a local web server in the background
echo "Starting local web server on port $PORT..."
python -m http.server $PORT &
SERVER_PID=$!

# Wait for the server to start
sleep 2

# Install required packages if not already installed
pip install selenium webdriver-manager

# Generate high-resolution export
echo "Generating high-resolution export..."
python tools/generate_deckgl_export.py \
  --html "$HTML_PATH" \
  --output-dir "$EXPORT_DIR" \
  --width 3840 \
  --height 2160 \
  --wait-time 10

# Check if export was successful
if [ $? -ne 0 ]; then
  echo "Warning: High-resolution export failed."
  echo "You can still use the browser's export functionality by visiting:"
  echo "http://localhost:$PORT/$HTML_PATH"
  echo "and clicking the 'Export PNG' button."
fi

# Stop the server
kill $SERVER_PID
echo "Server stopped."

echo "Done! Check $EXPORT_DIR for the exported image."
