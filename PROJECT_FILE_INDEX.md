# LOGhub Project File Index

This document serves as a comprehensive index of all relevant files in the LOGhub project, including their paths and functions. Use this as a reference to understand the project structure and locate specific files.

## Project Root

- `/LOGhub/` - Main project directory

## Configuration Files

| Path | Description |
|------|-------------|
| `/LOGhub/config/gee/gentle-cinema-458613-f3-51d8ea2711e7.json` | Google Earth Engine service account credentials |
| `/LOGhub/config/aoi/` | Area of Interest configuration files |

## Data Files

### Input Data

| Path | Description |
|------|-------------|
| `/LOGhub/data/tl_2024_us_county/tl_2024_us_county.shp` | US County shapefile (input) |

### Processed Data

| Path | Description |
|------|-------------|
| `/LOGhub/data/south/tile_scores.csv` | Tile scores for the South region |
| `/LOGhub/data/west/tile_scores.csv` | Tile scores for the West region |
| `/LOGhub/data/east/tile_scores.csv` | Tile scores for the East region |
| `/LOGhub/data/south/county_joined.geojson` | County-joined GeoJSON for South region |
| `/LOGhub/data/west/county_joined.geojson` | County-joined GeoJSON for West region |
| `/LOGhub/data/east/county_joined.geojson` | County-joined GeoJSON for East region |

### Final Data

| Path | Description |
|------|-------------|
| `/LOGhub/data/final/county_scores.geojson` | Combined county scores GeoJSON (final output) |
| `/LOGhub/data/validation/county_scores_validation.json` | Validation report for county scores |

## Tile Grid and Manifests

| Path | Description |
|------|-------------|
| `/LOGhub/tiles/` | Directory for tile grid files |
| `/LOGhub/manifests/` | Directory for export manifests |

## Python Tools

### Core Processing Tools

| Path | Description |
|------|-------------|
| `/LOGhub/tools/create_tile_grid.py` | Creates a grid of 256x256 pixel tiles over the AOI |
| `/LOGhub/tools/export_tiles.py` | Exports tiles to Google Cloud Storage |
| `/LOGhub/tools/create_manifest.py` | Creates a manifest of exported tiles |
| `/LOGhub/tools/load_tiles.py` | Loads tiles using PyTorch DataLoader |
| `/LOGhub/tools/process_tiles.py` | Processes tiles to generate obsolescence scores |

### Aggregation and Visualization Tools

| Path | Description |
|------|-------------|
| `/LOGhub/tools/aggregate_tiles_to_counties.py` | Aggregates tile-level results to county polygons |
| `/LOGhub/tools/visualize_county_scores.py` | Creates visualizations of county scores |
| `/LOGhub/tools/create_static_us_map.py` | Creates static PNG map of the US with county scores |
| `/LOGhub/tools/create_interactive_us_map.py` | Creates interactive HTML map of the US |
| `/LOGhub/tools/create_3d_interactive_map.py` | Creates 3D interactive map with height extrusion |

### Validation and Export Tools

| Path | Description |
|------|-------------|
| `/LOGhub/tools/validate_data.py` | Validates GeoJSON and CSV data quality |
| `/LOGhub/tools/generate_deckgl_export.py` | Generates high-resolution exports from Deck.gl |

## Shell Scripts

### Pipeline Scripts

| Path | Description |
|------|-------------|
| `/LOGhub/run_full_pipeline.sh` | Runs the complete pipeline from start to finish |
| `/LOGhub/aggregate_counties.sh` | Aggregates tile scores to counties for all regions |
| `/LOGhub/create_us_map_visualizations.sh` | Creates US map visualizations |
| `/LOGhub/create_phase2_visualizations.sh` | Creates Phase 2 visualizations |

### Utility Scripts

| Path | Description |
|------|-------------|
| `/LOGhub/run_deckgl_prototype.sh` | Validates data and opens the Deck.gl prototype |
| `/LOGhub/export_high_res_map.sh` | Generates high-resolution PNG export |
| `/LOGhub/phase2_complete.sh` | Runs all steps for Phase 2 |

## Visualization Outputs

### Static Visualizations

| Path | Description |
|------|-------------|
| `/LOGhub/visualizations/south_counties.png` | Static visualization of South region |
| `/LOGhub/visualizations/west_counties.png` | Static visualization of West region |
| `/LOGhub/visualizations/east_counties.png` | Static visualization of East region |
| `/LOGhub/visualizations/all_counties.png` | Static visualization of all regions |
| `/LOGhub/qa/full_us_map.png` | Static visualization of full US map |

### Interactive Visualizations

| Path | Description |
|------|-------------|
| `/LOGhub/visualizations/south_counties.html` | Interactive visualization of South region |
| `/LOGhub/visualizations/west_counties.html` | Interactive visualization of West region |
| `/LOGhub/visualizations/east_counties.html` | Interactive visualization of East region |
| `/LOGhub/visualizations/all_counties.html` | Interactive visualization of all regions |
| `/LOGhub/qa/full_us_map.html` | Interactive visualization of full US map |
| `/LOGhub/qa/full_us_map_3d_confidence.html` | 3D visualization with confidence as height |
| `/LOGhub/qa/full_us_map_3d_tile_count.html` | 3D visualization with tile count as height |
| `/LOGhub/qa/deck_gl_prototype.html` | Deck.gl prototype for county obsolescence scores |
| `/LOGhub/qa/deck_gl_simple.html` | Simplified Deck.gl example |

### Exports

| Path | Description |
|------|-------------|
| `/LOGhub/qa/exports/` | Directory for high-resolution exports |

## Documentation

| Path | Description |
|------|-------------|
| `/LOGhub/README.md` | Main project README |
| `/LOGhub/README_DECKGL.md` | Documentation for Deck.gl prototype |
| `/LOGhub/PROJECT_FILE_INDEX.md` | This file - comprehensive index of project files |

## Environment

| Path | Description |
|------|-------------|
| `/LOGhub/loghub_env/` | Python virtual environment |
| `/LOGhub/requirements.txt` | Python package requirements |

## File Path Resolution Guidelines

1. **Absolute Paths**: When specifying paths in configuration files or command-line arguments, use absolute paths:
   ```
   /Users/yairtitelboim/Documents/Kernel/ALLAPPS/LOGhub/data/tl_2024_us_county/tl_2024_us_county.shp
   ```

2. **Relative Paths in Scripts**: When using paths in Python scripts or shell scripts, use paths relative to the LOGhub directory:
   ```
   data/tl_2024_us_county/tl_2024_us_county.shp
   ```

3. **Relative Paths in HTML/JavaScript**: When referencing files from HTML or JavaScript, use paths relative to the HTML file location:
   ```
   ../data/final/county_scores.geojson
   ```

4. **Environment Variables**: For flexibility, consider using environment variables for base paths:
   ```bash
   export LOGHUB_ROOT="/Users/yairtitelboim/Documents/Kernel/ALLAPPS/LOGhub"
   ```

## Common Path Issues and Solutions

1. **Issue**: Python scripts can't find data files
   **Solution**: Make sure you're running scripts from the LOGhub directory or use absolute paths

2. **Issue**: HTML visualizations can't load GeoJSON data
   **Solution**: Run a local web server (e.g., `python -m http.server 8000`) and access via http://localhost:8000/

3. **Issue**: Shell scripts can't find Python scripts
   **Solution**: Make sure all scripts are executable (`chmod +x script.py`) and use correct relative paths

4. **Issue**: Google Earth Engine can't find credential file
   **Solution**: Use the absolute path to the credential file in the configuration
