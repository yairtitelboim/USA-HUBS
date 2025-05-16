# LOGhub Project Structure

This document provides a visual representation of the LOGhub project structure to help understand the organization of files and directories.

```
LOGhub/
│
├── config/                         # Configuration files
│   ├── aoi/                        # Area of Interest configurations
│   └── gee/                        # Google Earth Engine credentials
│       └── gentle-cinema-458613-f3-51d8ea2711e7.json
│
├── data/                           # Data files
│   ├── east/                       # East region data
│   │   ├── tile_scores.csv         # Tile scores for East region
│   │   └── county_joined.geojson   # County-joined GeoJSON for East
│   │
│   ├── south/                      # South region data
│   │   ├── tile_scores.csv         # Tile scores for South region
│   │   └── county_joined.geojson   # County-joined GeoJSON for South
│   │
│   ├── west/                       # West region data
│   │   ├── tile_scores.csv         # Tile scores for West region
│   │   └── county_joined.geojson   # County-joined GeoJSON for West
│   │
│   ├── final/                      # Final output data
│   │   └── county_scores.geojson   # Combined county scores
│   │
│   ├── validation/                 # Validation reports
│   │   └── county_scores_validation.json
│   │
│   └── tl_2024_us_county/          # US County shapefile
│       └── tl_2024_us_county.shp
│
├── manifests/                      # Export manifests
│
├── qa/                             # Quality assurance outputs
│   ├── exports/                    # High-resolution exports
│   ├── full_us_map.png             # Static US map
│   ├── full_us_map.html            # Interactive US map
│   ├── full_us_map_3d_confidence.html  # 3D map with confidence height
│   ├── full_us_map_3d_tile_count.html  # 3D map with tile count height
│   ├── deck_gl_prototype.html      # Deck.gl prototype
│   └── deck_gl_simple.html         # Simplified Deck.gl example
│
├── tiles/                          # Tile grid files
│
├── tools/                          # Python tools
│   ├── create_tile_grid.py         # Creates tile grid
│   ├── export_tiles.py             # Exports tiles to GCS
│   ├── create_manifest.py          # Creates export manifest
│   ├── load_tiles.py               # Loads tiles with PyTorch
│   ├── process_tiles.py            # Processes tiles
│   ├── aggregate_tiles_to_counties.py  # Aggregates to counties
│   ├── visualize_county_scores.py  # Creates visualizations
│   ├── create_static_us_map.py     # Creates static map
│   ├── create_interactive_us_map.py  # Creates interactive map
│   ├── create_3d_interactive_map.py  # Creates 3D map
│   ├── validate_data.py            # Validates data quality
│   └── generate_deckgl_export.py   # Generates high-res exports
│
├── visualizations/                 # Visualization outputs
│   ├── south_counties.png          # South region static viz
│   ├── west_counties.png           # West region static viz
│   ├── east_counties.png           # East region static viz
│   ├── all_counties.png            # All regions static viz
│   ├── south_counties.html         # South region interactive viz
│   ├── west_counties.html          # West region interactive viz
│   ├── east_counties.html          # East region interactive viz
│   └── all_counties.html           # All regions interactive viz
│
├── loghub_env/                     # Python virtual environment
│
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
└── PROJECT_STRUCTURE.md            # This file - visual structure
```

## Data Flow Diagram

The following diagram illustrates the data flow through the LOGhub pipeline:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Satellite   │     │ Tile Grid   │     │ Batch       │     │ Tile        │
│ Imagery     │────▶│ Generation  │────▶│ Export      │────▶│ Processing  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
                                                                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Interactive │     │ County      │     │ Validation  │     │ Tile-County │
│ Viz         │◀────│ Aggregation │◀────│ & QA        │◀────│ Joining     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

## Phase 1 vs Phase 2 Files

### Phase 1 Files (Tile Processing)
- `tools/create_tile_grid.py`
- `tools/export_tiles.py`
- `tools/create_manifest.py`
- `tools/load_tiles.py`
- `tools/process_tiles.py`
- `data/*/tile_scores.csv`

### Phase 2 Files (Visualization)
- `tools/aggregate_tiles_to_counties.py`
- `tools/visualize_county_scores.py`
- `tools/create_static_us_map.py`
- `tools/create_interactive_us_map.py`
- `tools/create_3d_interactive_map.py`
- `tools/validate_data.py`
- `tools/generate_deckgl_export.py`
- `qa/deck_gl_prototype.html`
- `data/final/county_scores.geojson`

## Script Dependencies

```
phase2_complete.sh
  ├── tools/create_static_us_map.py
  ├── tools/create_interactive_us_map.py
  ├── tools/create_3d_interactive_map.py
  ├── tools/validate_data.py
  └── run_deckgl_prototype.sh
      └── tools/validate_data.py

export_high_res_map.sh
  └── tools/generate_deckgl_export.py
```

## Common Path Resolution Patterns

1. **Python Scripts**: 
   ```python
   import os
   
   # Get the project root directory
   project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
   
   # Construct paths relative to the project root
   data_path = os.path.join(project_root, 'data', 'final', 'county_scores.geojson')
   ```

2. **Shell Scripts**:
   ```bash
   # Define the project root
   PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   
   # Construct paths relative to the project root
   DATA_PATH="${PROJECT_ROOT}/data/final/county_scores.geojson"
   ```

3. **HTML/JavaScript**:
   ```javascript
   // Use relative paths from the HTML file location
   fetch('../data/final/county_scores.geojson')
     .then(response => response.json())
     .then(data => {
       // Process data
     });
   ```
