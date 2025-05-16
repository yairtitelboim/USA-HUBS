import React, { useRef, useEffect, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

// Mapbox token from environment variable
mapboxgl.accessToken = process.env.REACT_APP_MAPBOX_ACCESS_TOKEN || 'pk.eyJ1IjoieWFpcnRpdGVsIiwiYSI6ImNsZm1wODZuNzAyNmIzcHAydTRsaWlpOTIifQ.OG_0yvbvyo6gbqOJuP1Q3g';

const MapComponent = () => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [loading, setLoading] = useState(true);

  // Initialize the map
  useEffect(() => {
    if (map.current) return; // Initialize map only once

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
      console.log('Loading county data from GeoJSON file...');

      // Fetch the county data from the GeoJSON file
      fetch('/data/final/county_scores.geojson')
        .then(response => {
          if (!response.ok) {
            console.error('Failed to load county data:', response.status);
            throw new Error('County data not found');
          }
          return response.json();
        })
        .then(countyData => {
          console.log(`Loaded ${countyData.features.length} counties with real data`);

          // Add the source with the fetched data
          map.current.addSource('counties', {
            type: 'geojson',
            data: countyData,
            maxzoom: 12,
            buffer: 128,
            tolerance: 0.375
          });
        })
        .then(() => {
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
        })
        .catch(error => {
          console.error('Error loading county data:', error);
          alert('Error loading county data. Please check the console for details.');
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
      <div ref={mapContainer} className="map" />
    </div>
  );
};

export default MapComponent;
