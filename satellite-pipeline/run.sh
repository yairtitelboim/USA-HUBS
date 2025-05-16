#!/bin/bash
#
# Satellite Data Pipeline Runner
#
# This script provides commands to run various components of the satellite data pipeline.
# Usage: ./run.sh [command]
#
# Commands:
#   collect      - Run data collection for the most recent time period
#   historical   - Process historical data
#   api          - Start the API server
#   dashboard    - Start the dashboard server
#   all          - Start API and dashboard servers
#   help         - Show this help message

# Set default values
PYTHON=${PYTHON:-python}
LOG_DIR="logs"
CONFIG_DIR="config"
PIPELINE_DIR=$(dirname "$0")

# Ensure we're in the pipeline directory
cd "$PIPELINE_DIR" || { echo "Error: Could not change to pipeline directory: $PIPELINE_DIR"; exit 1; }

# Create necessary directories
mkdir -p "$LOG_DIR"

# Function to show help message
show_help() {
  echo "Satellite Data Pipeline Runner"
  echo
  echo "Usage: ./run.sh [command]"
  echo
  echo "Commands:"
  echo "  collect [options]   - Run data collection for the most recent time period"
  echo "  historical [options] - Process historical data"
  echo "  api                 - Start the API server"
  echo "  dashboard           - Start the dashboard server"
  echo "  all                 - Start API and dashboard servers"
  echo "  help                - Show this help message"
  echo
  echo "Examples:"
  echo "  ./run.sh collect --test"
  echo "  ./run.sh historical --start-date 2020-01-01 --end-date 2023-12-31 --interval quarterly"
  echo "  ./run.sh all"
}

# Function to run data collection
run_collection() {
  echo "Running data collection with options: $*"
  "$PYTHON" scripts/collect_data.py "$@" >> "$LOG_DIR/collection_run.log" 2>&1 &
  echo "Collection started in background (PID: $!). Check $LOG_DIR/collection_run.log for output."
}

# Function to run historical data processing
run_historical() {
  echo "Running historical data processing with options: $*"
  "$PYTHON" scripts/process_historical.py "$@" >> "$LOG_DIR/historical_run.log" 2>&1 &
  echo "Historical processing started in background (PID: $!). Check $LOG_DIR/historical_run.log for output."
}

# Function to start the API server
run_api() {
  # Load settings from YAML
  API_HOST=$(grep -A2 "api:" "$CONFIG_DIR/settings.yaml" | grep "host:" | awk '{print $2}' | tr -d '"')
  API_PORT=$(grep -A3 "api:" "$CONFIG_DIR/settings.yaml" | grep "port:" | awk '{print $2}' | tr -d '"')
  
  API_HOST=${API_HOST:-localhost}
  API_PORT=${API_PORT:-8000}
  
  echo "Starting API server at $API_HOST:$API_PORT"
  cd src/api || { echo "Error: API directory not found"; exit 1; }
  "$PYTHON" server.py --host "$API_HOST" --port "$API_PORT" >> "../../$LOG_DIR/api.log" 2>&1 &
  API_PID=$!
  cd ../.. || exit
  
  echo "API server started (PID: $API_PID)"
  return "$API_PID"
}

# Function to start the dashboard server
run_dashboard() {
  echo "Starting dashboard server at localhost:5000"
  cd src/dashboard || { echo "Error: Dashboard directory not found"; exit 1; }
  "$PYTHON" server.py --host localhost --port 5000 >> "../../$LOG_DIR/dashboard.log" 2>&1 &
  DASHBOARD_PID=$!
  cd ../.. || exit
  
  echo "Dashboard server started (PID: $DASHBOARD_PID)"
  return "$DASHBOARD_PID"
}

# Parse command
COMMAND=${1:-help}
shift || true

case "$COMMAND" in
  collect)
    run_collection "$@"
    ;;
    
  historical)
    run_historical "$@"
    ;;
    
  api)
    run_api
    ;;
    
  dashboard)
    run_dashboard
    ;;
    
  all)
    echo "Starting all services..."
    API_PID=$(run_api)
    DASHBOARD_PID=$(run_dashboard)
    
    echo "All services started. Press Ctrl+C to stop."
    echo "API PID: $API_PID"
    echo "Dashboard PID: $DASHBOARD_PID"
    
    # Write PIDs to file for easier cleanup
    echo "$API_PID $DASHBOARD_PID" > "$LOG_DIR/service_pids.txt"
    
    # Handle Ctrl+C to stop all services gracefully
    trap 'echo "Stopping services..."; kill $(cat "$LOG_DIR/service_pids.txt") 2>/dev/null; rm "$LOG_DIR/service_pids.txt"; echo "Services stopped."; exit 0' INT
    
    # Wait until killed
    while true; do
      sleep 1
    done
    ;;
    
  help|*)
    show_help
    ;;
esac