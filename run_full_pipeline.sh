#!/bin/bash

# Run the full satellite imagery pipeline region by region
# This script runs all steps of the Phase 1 pipeline for each region

# Activate the Python environment
source loghub_env/bin/activate

# Set common variables
START_DATE="2023-11-01"
END_DATE="2025-05-01"
BUCKET="loghub-sentinel2-exports"
PROJECT="gentle-cinema-458613-f3"
CHUNK_SIZE=500
SAMPLE_SIZE=100

# Define regions
REGIONS=("south" "west" "east")

# Process each region
for REGION in "${REGIONS[@]}"; do
    echo "=========================================="
    echo "Processing region: $REGION"
    echo "=========================================="

    # Set region-specific variables
    AOI_PATH="config/aoi/us_${REGION}.geojson"
    REGION_PREFIX="${REGION}"

    # Create timestamp
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)

    # Step 1: Generate & Review AOI Tile Grid
    echo "Step 1: Generating tile grid for $REGION region..."
    python examples/full_aoi_pipeline.py --aoi $AOI_PATH --skip-export --skip-monitor --skip-manifest --skip-benchmark

    # Pause for user review
    echo "Please review the tile grid in QGIS or geojson.io before proceeding."
    read -p "Press Enter to continue..."

    # Get the most recent tile grid file
    TILE_GRID=$(ls -t tiles/*.json | head -1)
    echo "Using tile grid: $TILE_GRID"

    # Step 2: Configure & Kick Off Batch Exports
    echo "Step 2: Configuring and kicking off batch exports for $REGION region..."
    python examples/full_aoi_pipeline.py --aoi $AOI_PATH --start-date $START_DATE --end-date $END_DATE --bucket $BUCKET --project $PROJECT --chunk-size $CHUNK_SIZE --skip-grid --skip-monitor --skip-manifest --skip-benchmark

    # Step 3: Monitor & Retry Failures
    echo "Step 3: Monitoring and retrying failures for $REGION region..."
    python monitor_ee_tasks.py --project $PROJECT --retry-failed --cancel-stalled --report qa/tasks_${REGION}_${TIMESTAMP}.json

    # Step 4: Build & Audit the Manifest
    echo "Step 4: Building and auditing the manifest for $REGION region..."
    python create_manifest.py $BUCKET --prefix "${REGION_PREFIX}" --start-date $START_DATE --end-date $END_DATE --manifest manifests/manifest_${REGION}_${TIMESTAMP}.txt --download --sample-size $SAMPLE_SIZE --analyze --report qa/sample_analysis_${REGION}_${TIMESTAMP}.json --mosaic --mosaic-output qa/mosaic_${REGION}_${TIMESTAMP}.png

    # Step 5: Ingest & Benchmark with PyTorch Dataset
    echo "Step 5: Ingesting and benchmarking with PyTorch Dataset for $REGION region..."
    python test_data_loader.py --manifest manifests/manifest_${REGION}_${TIMESTAMP}.txt --data-dir data/raw --sample-size $SAMPLE_SIZE --output-dir qa/test_plots_${REGION}_${TIMESTAMP}

    echo "$REGION region processing completed successfully!"
    echo ""

    # Ask if user wants to continue to the next region
    if [ "$REGION" != "${REGIONS[-1]}" ]; then
        read -p "Continue to the next region? (y/n): " CONTINUE
        if [ "$CONTINUE" != "y" ]; then
            echo "Pipeline execution stopped by user."
            exit 0
        fi
    fi
done

echo "Full pipeline completed successfully for all regions!"
