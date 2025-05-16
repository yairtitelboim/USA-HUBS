# County Map Visualization

This React application visualizes county data with 3D extrusions using Mapbox GL JS and Turf.js.

## Features

- 3D visualization of counties with extrusion heights based on confidence scores
- Color-coded counties based on obsolescence scores
- Interactive tooltips showing county details on hover
- Smooth navigation with zoom, pan, and rotate controls
- Dark mode UI for better visualization

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm (v6 or higher)

### Installation

1. Clone the repository
2. Navigate to the project directory
3. Install dependencies:

```bash
npm install
```

### Running the Application

Start the development server:

```bash
npm start
```

This will:
1. Run the data setup script to copy county GeoJSON data (if available)
2. Start the React development server
3. Open the application in your default browser at [http://localhost:3000](http://localhost:3000)

## Data Sources

The application will try to use real county data from `../data/final/county_scores.geojson`. If this file is not available, it will fall back to using mock data generated with Turf.js.

## Technologies Used

- React
- Mapbox GL JS
- Turf.js
- CSS3 for styling

## License

This project is licensed under the MIT License.
