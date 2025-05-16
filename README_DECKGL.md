# Deck.gl Prototype for County Obsolescence Scores

This README provides instructions for using the Deck.gl prototype for visualizing county obsolescence scores.

## Overview

The Deck.gl prototype visualizes county-level obsolescence scores across the United States. It features:

- 3D extrusion based on confidence or tile count
- Color mapping based on obsolescence score
- Interactive filtering by score and tile count
- Top 10 risk counties table
- High-resolution PNG export

## Running the Prototype

### Method 1: Using a Local Web Server (Recommended)

For full functionality, run the prototype using a local web server:

1. Open a terminal and navigate to the project root directory:
   ```bash
   cd /path/to/LOGhub
   ```

2. Start a Python HTTP server:
   ```bash
   python -m http.server 8000
   ```

3. Open a web browser and navigate to:
   ```
   http://localhost:8000/qa/deck_gl_prototype.html
   ```

This method allows the prototype to load the GeoJSON data from the file system.

### Method 2: Direct File Access

You can also open the HTML file directly in a browser:

```
file:///path/to/LOGhub/qa/deck_gl_prototype.html
```

When running directly from the file system, the prototype will use embedded mock data instead of loading the GeoJSON file due to browser security restrictions.

## Using the Prototype

### Basic Controls

- **3D Extrusion**: Toggle the checkbox to enable/disable 3D extrusion
- **Height Dimension**: Choose between "Confidence" or "Tile Count" for the height dimension
- **Obsolescence Score Filter**: Adjust the slider to filter counties by minimum score
- **Tile Count Filter**: Adjust the slider to filter counties by minimum tile count

### Advanced Features

- **Export PNG**: Click the "Export PNG" button to save a screenshot of the current view
- **Top 10 Counties**: Click the "Top 10 Counties" button to show/hide the table of top risk counties
- **Tooltips**: Hover over a county to see detailed information

## Data Validation

Before using the prototype with real data, validate the data quality:

```bash
python tools/validate_data.py --input data/final/county_scores.geojson --output data/validation/county_scores_validation.json --type geojson
```

This will check for issues such as missing values, invalid ranges, and other data quality problems.

## High-Resolution Export

For high-resolution exports (e.g., for presentations), use the export script:

```bash
python tools/generate_deckgl_export.py --html qa/deck_gl_prototype.html --output-dir qa/exports --width 3840 --height 2160
```

This requires Chrome and the Selenium package.

## Troubleshooting

### Error Loading GeoJSON Data

If you see an error about loading GeoJSON data:

1. Make sure you're running the prototype using a local web server (Method 1 above)
2. Check that the GeoJSON file exists at `data/final/county_scores.geojson`
3. Validate the GeoJSON file using the validation script

### Map Not Rendering

If the map is not rendering properly (no visual map appears):

1. Try the simplified version at `qa/deck_gl_simple.html` to see if it works
2. If the simple version works but the main prototype doesn't, there might be an issue with the Deck.gl library version or initialization
3. Check the browser console for specific error messages
4. Make sure you're using a modern browser (Chrome, Firefox, Safari, or Edge)

### Browser Compatibility

The prototype works best with modern browsers:
- Chrome (recommended)
- Firefox
- Safari
- Edge

Internet Explorer is not supported.

## Next Steps

For Phase 3, we plan to:
1. Integrate ensemble results
2. Add more advanced filtering options
3. Implement time-series visualization
4. Enhance the UI for better user experience
