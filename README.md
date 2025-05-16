# LOGhub Sentinel-2 Processing Pipeline

This repository contains scripts for processing Sentinel-2 satellite imagery for the LOGhub project.

## Setup

1. Create a Python virtual environment:
   ```bash
   python -m venv loghub_env
   source loghub_env/bin/activate
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Google Earth Engine authentication:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   ```

## Production Pipeline

The production pipeline consists of the following phases:

### Phase 1: Production-Scale Satellite Imagery Pipeline

Run the full pipeline with a single command:

```bash
./run_full_pipeline.sh
```

This script will:
1. Generate a tile grid for the full AOI
2. Configure and kick off batch exports
3. Monitor and retry failed tasks
4. Build and audit the manifest
5. Ingest and benchmark with PyTorch Dataset
6. Generate visual QA mosaics

You can also run each step individually using the `full_aoi_pipeline.py` script:

```bash
python examples/full_aoi_pipeline.py --aoi config/aoi/aoi_full.geojson
```

### Phase 2: County-Level Aggregation and Visualization

Run the complete Phase 2 pipeline with:

```bash
./phase2_complete.sh
```

This script will:
1. Aggregate tile-level results to county polygons
2. Generate static and interactive visualizations
3. Create 3D visualizations with height extrusion
4. Validate the data quality
5. Open the Deck.gl prototype for interactive exploration

You can also run the Deck.gl prototype directly:

```bash
./run_deckgl_prototype.sh
```

For high-resolution exports:

```bash
./export_high_res_map.sh
```

For more information about the Deck.gl prototype, see [README_DECKGL.md](README_DECKGL.md).

## Individual Workflow Steps

### 1. Create a Tile Grid

Generate a grid of tiles covering your Area of Interest (AOI):

```bash
python create_tile_grid.py --bbox -95.37 29.74 -95.36 29.75 --tile-size 256 --resolution 10
```

Or use a GeoJSON file as input:

```bash
python create_tile_grid.py --aoi-file path/to/aoi.geojson --tile-size 256 --resolution 10
```

This will create two files in the `tiles` directory:
- `tiles_YYYYMMDD_HHMMSS.geojson`: GeoJSON file with the tile grid
- `tiles_YYYYMMDD_HHMMSS.json`: Simplified JSON file for Earth Engine exports

### 2. Configure a Cloud Storage Bucket

Create a Google Cloud Storage bucket for exports:

```bash
gsutil mb gs://loghub-sentinel2-exports
```

Grant your service account write access:

```bash
gsutil iam ch serviceAccount:loghub-ee-sa@gentle-cinema-458613-f3.iam.gserviceaccount.com:objectAdmin gs://loghub-sentinel2-exports
```

### 3. Batch Export Sentinel-2 Imagery

Export Sentinel-2 imagery for each tile and date:

```bash
python batch_export_sentinel2.py tiles/tiles_YYYYMMDD_HHMMSS.json 2023-11-01 2025-05-01 --bucket loghub-sentinel2-exports --project gentle-cinema-458613-f3
```

This will submit Earth Engine tasks to export Sentinel-2 imagery for each tile and month.

### 4. Monitor Export Tasks

Monitor the status of export tasks:

```bash
python monitor_ee_tasks.py --project gentle-cinema-458613-f3 --status RUNNING --monitor
```

Retry failed tasks:

```bash
python monitor_ee_tasks.py --project gentle-cinema-458613-f3 --status FAILED --retry --bucket loghub-sentinel2-exports
```

Cancel stalled tasks:

```bash
python monitor_ee_tasks.py --project gentle-cinema-458613-f3 --cancel-stalled
```

Save a report of task status:

```bash
python monitor_ee_tasks.py --project gentle-cinema-458613-f3 --report qa/task_report.json
```

### 5. Create a Manifest and Download Samples

Create a manifest of exported files:

```bash
python create_manifest.py loghub-sentinel2-exports --start-date 2023-11-01 --end-date 2025-05-01
```

Download a sample of files for quality control:

```bash
python create_manifest.py loghub-sentinel2-exports --start-date 2023-11-01 --end-date 2025-05-01 --download --sample-size 100 --analyze --mosaic
```

This will:
- Create a manifest of all exported files
- Download a sample of 100 files
- Analyze the samples for cloud cover and other statistics
- Create a mosaic image for visual inspection

### 6. Load the Data

Use the `Sentinel2TileDataset` class to load the data:

```python
from loghub.data_loader import Sentinel2TileDataset

# Load data from a manifest
dataset = Sentinel2TileDataset(manifest_path='manifests/manifest.txt', data_dir='data/raw')

# Or load data from a directory
dataset = Sentinel2TileDataset(data_dir='data/raw')

# Get a tile
data, metadata = dataset[0]
```

Benchmark the dataset loading performance:

```bash
python test_data_loader.py --manifest manifests/manifest.txt --data-dir data/raw --sample-size 100
```

## Project Documentation

For detailed information about the project structure and file organization, please refer to the following documentation:

- [Project File Index](PROJECT_FILE_INDEX.md) - Comprehensive index of all files with their paths and functions
- [Project Structure](PROJECT_STRUCTURE.md) - Visual representation of the project structure with data flow diagrams
- [File Operations Guide](FILE_OPERATIONS_GUIDE.md) - Quick reference guide for common file operations

These documents will help you navigate the project and understand the relationships between different files and components.

## Directory Structure

```
LOGhub/
├── config/                         # Configuration files
│   ├── aoi/                        # Area of Interest configurations
│   └── gee/                        # Google Earth Engine credentials
│       └── gentle-cinema-458613-f3-51d8ea2711e7.json
│
├── data/                           # Data files
│   ├── east/                       # East region data
│   ├── south/                      # South region data
│   ├── west/                       # West region data
│   ├── final/                      # Final output data
│   ├── validation/                 # Validation reports
│   ├── tl_2024_us_county/          # US County shapefile
│   └── raw/                        # Downloaded Sentinel-2 tiles
│
├── manifests/                      # Export manifests
├── qa/                             # Quality assurance outputs
├── tiles/                          # Tile grid files
├── tools/                          # Python tools
├── visualizations/                 # Visualization outputs
│
├── loghub_env/                     # Python virtual environment
├── requirements.txt                # Python package requirements
│
├── run_full_pipeline.sh            # Full pipeline script
├── aggregate_counties.sh           # County aggregation script
├── create_us_map_visualizations.sh # US map viz script
├── create_phase2_visualizations.sh # Phase 2 viz script
├── run_deckgl_prototype.sh         # Deck.gl prototype script
├── export_high_res_map.sh          # High-res export script
├── phase2_complete.sh              # Phase 2 complete script
│
├── README.md                       # Main project README
├── README_DECKGL.md                # Deck.gl prototype docs
├── PROJECT_FILE_INDEX.md           # Comprehensive file index
├── PROJECT_STRUCTURE.md            # Visual structure
└── FILE_OPERATIONS_GUIDE.md        # File operations guide
```

## Performance Benchmarks

Expected performance:
- Tile loading speed: < 0.2 seconds per tile
- Export time: ~20 seconds per tile for a small AOI
- Cloud cover: < 50% for most tiles

## Next Steps

1. Quality and Performance QA:
   - Check coverage against the tile grid
   - Compute cloud cover statistics
   - Benchmark loading speed
   - Visual inspection of samples

2. Integration with CV Pipeline:
   - Use the `Sentinel2TileDataset` class in your training and inference scripts
   - Confirm forward-pass on a 256×256 crop
   - Log IoU or traffic-density sanity checks
