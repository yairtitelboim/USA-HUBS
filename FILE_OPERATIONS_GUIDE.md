# LOGhub File Operations Quick Reference Guide

This guide provides quick reference for common file operations in the LOGhub project.

## Running Python Scripts

### From Project Root

```bash
# Activate the virtual environment
source loghub_env/bin/activate

# Run a Python script from the tools directory
python tools/validate_data.py --input data/final/county_scores.geojson --output data/validation/county_scores_validation.json --type geojson
```

### With Absolute Paths

```bash
# Activate the virtual environment
source loghub_env/bin/activate

# Run a Python script with absolute paths
python tools/aggregate_tiles_to_counties.py \
  --tile-scores /Users/yairtitelboim/Documents/Kernel/ALLAPPS/LOGhub/data/south/tile_scores.csv \
  --county-shp /Users/yairtitelboim/Documents/Kernel/ALLAPPS/LOGhub/data/tl_2024_us_county/tl_2024_us_county.shp \
  --output /Users/yairtitelboim/Documents/Kernel/ALLAPPS/LOGhub/data/south/county_joined.geojson
```

## Running Shell Scripts

```bash
# Make the script executable (only needed once)
chmod +x run_deckgl_prototype.sh

# Run the script
./run_deckgl_prototype.sh
```

## Serving HTML Files

```bash
# Start a local web server
python -m http.server 8000

# Access in browser
# http://localhost:8000/qa/deck_gl_prototype.html
```

## Checking File Existence

```bash
# Check if a file exists
ls -la data/final/county_scores.geojson

# Check file content
head -n 20 data/final/county_scores.geojson
```

## Creating Directories

```bash
# Create directories if they don't exist
mkdir -p data/validation qa/exports
```

## Common File Paths by Task

### Data Validation

```bash
# Validate GeoJSON data
python tools/validate_data.py \
  --input data/final/county_scores.geojson \
  --output data/validation/county_scores_validation.json \
  --type geojson
```

### Visualization Generation

```bash
# Generate static US map
python tools/create_static_us_map.py \
  --output qa/full_us_map.png \
  --use-mock-data \
  --county-shp data/tl_2024_us_county/tl_2024_us_county.shp

# Generate interactive US map
python tools/create_interactive_us_map.py \
  --output qa/full_us_map.html \
  --use-mock-data \
  --county-shp data/tl_2024_us_county/tl_2024_us_county.shp

# Generate 3D interactive map
python tools/create_3d_interactive_map.py \
  --output qa/full_us_map_3d_confidence.html \
  --height-field confidence \
  --use-mock-data \
  --county-shp data/tl_2024_us_county/tl_2024_us_county.shp
```

### Running the Deck.gl Prototype

```bash
# Run the Deck.gl prototype
./run_deckgl_prototype.sh

# Generate high-resolution export
./export_high_res_map.sh
```

### Complete Phase 2 Setup

```bash
# Run all Phase 2 steps
./phase2_complete.sh
```

## File Path Resolution in Code

### Python

```python
import os

def get_project_root():
    """Get the absolute path to the project root directory."""
    # Assuming this function is in a module in the tools directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  # Go up one level from tools/
    return project_root

def resolve_path(relative_path):
    """Resolve a path relative to the project root."""
    return os.path.join(get_project_root(), relative_path)

# Example usage
county_shp_path = resolve_path('data/tl_2024_us_county/tl_2024_us_county.shp')
output_path = resolve_path('data/south/county_joined.geojson')
```

### Shell Scripts

```bash
#!/bin/bash

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to resolve paths relative to the project root
resolve_path() {
    echo "${PROJECT_ROOT}/$1"
}

# Example usage
COUNTY_SHP="$(resolve_path data/tl_2024_us_county/tl_2024_us_county.shp)"
OUTPUT_DIR="$(resolve_path qa)"
```

### HTML/JavaScript

```javascript
// Function to resolve relative paths in browser context
function resolvePath(relativePath) {
    // Get the base URL (up to the last /)
    const baseUrl = window.location.href.substring(0, window.location.href.lastIndexOf('/') + 1);
    
    // Handle ../ in the relative path
    let path = relativePath;
    if (path.startsWith('../')) {
        // Go up one directory level in the base URL
        const newBaseUrl = baseUrl.substring(0, baseUrl.slice(0, -1).lastIndexOf('/') + 1);
        path = path.substring(3); // Remove the '../'
        return newBaseUrl + path;
    }
    
    return baseUrl + path;
}

// Example usage
fetch(resolvePath('../data/final/county_scores.geojson'))
    .then(response => response.json())
    .then(data => {
        // Process data
    });
```

## Troubleshooting Common Path Issues

### Issue: "File not found" errors

**Solution**: 
1. Check if you're in the correct directory (should be LOGhub/)
2. Use absolute paths if necessary
3. Check file permissions

### Issue: "Permission denied" when running scripts

**Solution**:
```bash
chmod +x script_name.sh
chmod +x tools/script_name.py
```

### Issue: HTML can't load local files

**Solution**:
1. Start a local web server: `python -m http.server 8000`
2. Access via http://localhost:8000/path/to/file.html
3. For file:// protocol, use the embedded mock data option

### Issue: Python can't find modules

**Solution**:
1. Make sure you've activated the virtual environment: `source loghub_env/bin/activate`
2. Check if the module is installed: `pip list | grep module_name`
3. Install missing modules: `pip install module_name`

## Best Practices

1. **Always use relative paths** in code that will be shared or moved
2. **Include path resolution functions** in scripts and modules
3. **Create directories before writing files** using `mkdir -p`
4. **Validate file existence** before attempting to read
5. **Use consistent naming conventions** for files and directories
6. **Document file paths** in comments and documentation
7. **Provide fallback options** for missing files (e.g., mock data)
8. **Use environment variables** for system-specific paths
