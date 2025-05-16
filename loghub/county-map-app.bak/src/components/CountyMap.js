import React, { useRef, useEffect, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import * as turf from '@turf/turf';
import 'mapbox-gl/dist/mapbox-gl.css';

// Mapbox token
mapboxgl.accessToken = 'pk.eyJ1IjoieWFpcnRpdGVsIiwiYSI6ImNsZm1wODZuNzAyNmIzcHAydTRsaWlpOTIifQ.OG_0yvbvyo6gbqOJuP1Q3g';

const CountyMap = () => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Color scale for obsolescence score
  const colorScale = [
    [0, [44, 123, 182]], // Low (blue)
    [0.5, [255, 255, 191]], // Medium (yellow)
    [1, [215, 25, 28]] // High (red)
  ];

  // Function to interpolate colors based on score
  const interpolateColor = (value) => {
    // Find the color range
    let lowerIndex = 0;
    for (let i = 1; i < colorScale.length; i++) {
      if (value <= colorScale[i][0]) {
        lowerIndex = i - 1;
        break;
      }
    }

    const lowerValue = colorScale[lowerIndex][0];
    const upperValue = colorScale[lowerIndex + 1][0];
    const lowerColor = colorScale[lowerIndex][1];
    const upperColor = colorScale[lowerIndex + 1][1];

    // Calculate interpolation factor
    const range = upperValue - lowerValue;
    const factor = (value - lowerValue) / range;

    // Interpolate RGB values
    return [
      Math.round(lowerColor[0] + factor * (upperColor[0] - lowerColor[0])),
      Math.round(lowerColor[1] + factor * (upperColor[1] - lowerColor[1])),
      Math.round(lowerColor[2] + factor * (upperColor[2] - lowerColor[2]))
    ];
  };

  // Generate mock county data for testing
  const generateMockCountyData = () => {
    console.log("Generating mock county data");

    const mockData = {
      type: 'FeatureCollection',
      features: []
    };

    // Generate mock features for US counties across the country
    const counties = [
      // West Coast
      { name: 'Los Angeles County', state: 'CA', geoid: '06037', lon: -118.2437, lat: 34.0522, score: 0.82, confidence: 0.95, tiles: 18 },
      { name: 'San Diego County', state: 'CA', geoid: '06073', lon: -117.1611, lat: 32.7157, score: 0.57, confidence: 0.82, tiles: 9 },
      { name: 'King County', state: 'WA', geoid: '53033', lon: -122.3321, lat: 47.5480, score: 0.44, confidence: 0.71, tiles: 8 },
      
      // Midwest
      { name: 'Cook County', state: 'IL', geoid: '17031', lon: -87.6298, lat: 41.8781, score: 0.75, confidence: 0.92, tiles: 15 },
      { name: 'Wayne County', state: 'MI', geoid: '26163', lon: -83.2454, lat: 42.2791, score: 0.58, confidence: 0.83, tiles: 9 },
      
      // South
      { name: 'Harris County', state: 'TX', geoid: '48201', lon: -95.3698, lat: 29.7604, score: 0.68, confidence: 0.88, tiles: 12 },
      { name: 'Miami-Dade County', state: 'FL', geoid: '12086', lon: -80.1918, lat: 25.7617, score: 0.48, confidence: 0.76, tiles: 7 },
      
      // Northeast
      { name: 'New York County', state: 'NY', geoid: '36061', lon: -73.9712, lat: 40.7831, score: 0.72, confidence: 0.90, tiles: 14 },
      { name: 'Philadelphia County', state: 'PA', geoid: '42101', lon: -75.1652, lat: 39.9526, score: 0.51, confidence: 0.78, tiles: 8 }
    ];

    // Create a feature for each county
    counties.forEach(county => {
      // Create a circle for the county using Turf.js
      const center = [county.lon, county.lat];
      const radius = 1; // Radius in degrees
      const options = {steps: 64, units: 'degrees'};
      const circle = turf.circle(center, radius, options);
      
      // Add properties to the feature
      circle.properties = {
        NAME: county.name,
        STATEFP: county.state,
        GEOID: county.geoid,
        obsolescence_score: county.score,
        confidence: county.confidence,
        tile_count: county.tiles
      };
      
      mockData.features.push(circle);
    });

    console.log(`Generated ${mockData.features.length} mock counties`);
    return mockData;
  };

  // Initialize the map
  useEffect(() => {
    if (map.current) return; // Initialize map only once

    try {
      // Create the map
      map.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: 'mapbox://styles/mapbox/dark-v11',
        center: [-98.5795, 39.8283], // Center of the US
        zoom: 3.5,
        pitch: 60, // Start with 3D view
        bearing: 30 // Add some rotation for better 3D perspective
      });

      // Add navigation controls
      map.current.addControl(new mapboxgl.NavigationControl());

      // Wait for the map to load
      map.current.on('load', () => {
        // Generate mock data or fetch real data
        const geojsonData = generateMockCountyData();
        
        // Add a source for the county data
        map.current.addSource('counties', {
          type: 'geojson',
          data: geojsonData
        });

        // Add a fill-extrusion layer for 3D counties
        map.current.addLayer({
          id: 'county-extrusions',
          type: 'fill-extrusion',
          source: 'counties',
          paint: {
            'fill-extrusion-color': [
              'interpolate',
              ['linear'],
              ['get', 'obsolescence_score'],
              0, 'rgb(44, 123, 182)',
              0.5, 'rgb(255, 255, 191)',
              1, 'rgb(215, 25, 28)'
            ],
            'fill-extrusion-height': [
              '*',
              ['get', 'confidence'],
              500000 // Scale factor for height
            ],
            'fill-extrusion-base': 0,
            'fill-extrusion-opacity': 0.8
          }
        });

        // Add a line layer for county boundaries with thick white lines
        map.current.addLayer({
          id: 'county-borders',
          type: 'line',
          source: 'counties',
          paint: {
            'line-color': 'white',
            'line-width': 2,
            'line-opacity': 0.9
          }
        });

        // Create a popup for county information
        const popup = new mapboxgl.Popup({
          closeButton: false,
          closeOnClick: false
        });

        // Show popup on hover
        map.current.on('mouseenter', 'county-extrusions', (e) => {
          map.current.getCanvas().style.cursor = 'pointer';
          
          const feature = e.features[0];
          const props = feature.properties;
          
          // Get the center of the county for popup placement
          const coordinates = e.lngLat;
          
          // Create popup content
          const html = `
            <div style="color: #333;">
              <strong>${props.NAME}, ${props.STATEFP}</strong><br>
              Obsolescence Score: <strong>${parseFloat(props.obsolescence_score).toFixed(2)}</strong><br>
              Confidence: ${parseFloat(props.confidence).toFixed(2)}<br>
              Tile Count: ${props.tile_count}
            </div>
          `;
          
          popup.setLngLat(coordinates)
            .setHTML(html)
            .addTo(map.current);
        });

        // Hide popup on mouseleave
        map.current.on('mouseleave', 'county-extrusions', () => {
          map.current.getCanvas().style.cursor = '';
          popup.remove();
        });

        // Loading complete
        setLoading(false);
      });
    } catch (err) {
      console.error('Error initializing map:', err);
      setError(err.message);
      setLoading(false);
    }

    // Clean up on unmount
    return () => {
      if (map.current) {
        map.current.remove();
      }
    };
  }, []);

  return (
    <div className="map-container">
      {loading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p>Loading map...</p>
        </div>
      )}
      {error && (
        <div className="error-message">
          <p>Error: {error}</p>
        </div>
      )}
      <div ref={mapContainer} className="map" />
    </div>
  );
};

export default CountyMap;
