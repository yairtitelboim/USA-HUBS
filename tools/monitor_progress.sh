#!/bin/bash
# Simple script to monitor progress periodically

# Default interval is 5 minutes (300 seconds)
INTERVAL=${1:-300}

echo "Monitoring progress every $INTERVAL seconds. Press Ctrl+C to stop."
echo ""

while true; do
    # Clear the screen
    clear
    
    # Print timestamp
    echo "=== Update at $(date) ==="
    echo ""
    
    # Run the progress check script
    python tools/check_progress.py
    
    # Print next update time
    echo ""
    echo "Next update in $INTERVAL seconds (at $(date -v +${INTERVAL}S))"
    echo "Press Ctrl+C to stop monitoring"
    
    # Wait for the specified interval
    sleep $INTERVAL
done
