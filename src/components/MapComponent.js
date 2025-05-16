import React, { useEffect, useRef, useState } from 'react';
import Legend from '../Legend';
import MapControls from '../MapControls';
import RoadTraffic from '../RoadTraffic';
import '../MapComponent.css';
import '../MapboxPopups.css';
import '../../styles/CustomGradients.css';

// Import layer creators
import { 
  createCountyFillLayer,
  createSingleExtrusionLayer,
  createBaseExtrusionLayer,
  createMiddleExtrusionLayer,
  createCapExtrusionLayer,
  getObsolescenceHeightExpression,
  getGrowthHeightExpression
} from './map/layers/countyLayers';

// Import bivariate layer creators
import {
  addBivariateLayers,
  toggleBivariateView
} from './map/layers/bivariateLayers';

// Import overlay layer creators
import {
  createStateBoundariesLayer,
  createWaterBodiesLayer,
  createWaterwaysLayer,
  createMajorRoadsLayer,
  createSecondaryRoadsLayer,
  createCityLabelsLayer,
  getLayerOrdering,
  bringWaterAndRoadsToTop
} from './map/layers/overlayLayers';

// Import Amazon fulfillment center functions
import {
  addAmazonFulfillmentCenters,
  toggleAmazonMarkers
} from './map/layers/amazonMarkers';

// Import UPS facility marker functions
import { 
  addUPSFacilities,
  toggleUPSMarkers 
} from './map/layers/upsMarkers';

// Import rail facility marker functions
import {
  addRailFacilities,
  toggleRailMarkers
} from './map/layers/railMarkers';

/**
 * Utility function to toggle between metrics
 * @param {Object} map - The Mapbox map instance
 * @param {string} currentMetric - Current metric being displayed
 * @param {boolean} is3D - Whether the map is in 3D mode
 * @returns {string} The new metric after toggling
 */
const toggleMetricUtil = (map, currentMetric, is3D) => {
  const newMetric = currentMetric === 'obsolescence_score' 
    ? 'growth_potential_score' 
    : 'obsolescence_score';
  
  // Update layer visibility and properties based on the new metric
  // Implementation would depend on your specific map setup
  
  return newMetric;
};

/**
 * Order layers in the map according to the specified order
 * @param {Object} map - The Mapbox map instance
 * @param {Array} layerOrder - Array of layer IDs in the desired order
 */
const orderLayers = (map, layerOrder) => {
  if (!map) return;
  
  // Process layers in reverse to ensure correct stacking order
  for (let i = 0; i < layerOrder.length; i++) {
    const layerId = layerOrder[i];
    if (map.getLayer(layerId)) {
      map.moveLayer(layerId);
    }
  }
};

const MapComponent = () => {
  // State for metric and view mode
  const currentMetricRef = useRef('obsolescence_score');
  const [loading, setLoading] = useState(true);
  const [currentMetric, setCurrentMetric] = useState('obsolescence_score');
  const [is3D, setIs3D] = useState(true);
  const observerRef = useRef(null);
  const mapRef = useRef(null);
  const mapboxglRef = useRef(null);
  const mapContainer = useRef(null);
  const hoverPopupRef = useRef(null);
  const clickPopupRef = useRef(null);

  // Add bivariate view state
  const [isBivariateView, setIsBivariateView] = useState(false); 
  
  // Add Amazon markers state
  const [showAmazonMarkers, setShowAmazonMarkers] = useState(false);
  
  // Add state for county animations
  const [showCountyAnimations, setShowCountyAnimations] = useState(false);
  
  // Add state for UPS markers
  const [showUPSMarkers, setShowUPSMarkers] = useState(true);
  
  // Add state for Rail markers
  const [showRailMarkers, setShowRailMarkers] = useState(false);

  // Add state for road layer visibility
  const [showRoadLayer, setShowRoadLayer] = useState(true);

  // Function to toggle road layer visibility
  const handleRoadLayerToggle = () => {
    if (!mapRef.current) return;
    
    const newVisible = !showRoadLayer;
    setShowRoadLayer(newVisible);
    
    // Toggle visibility of both major and secondary roads
    if (mapRef.current.getLayer('major-roads')) {
      mapRef.current.setLayoutProperty('major-roads', 'visibility', newVisible ? 'visible' : 'none');
    }
    if (mapRef.current.getLayer('secondary-roads')) {
      mapRef.current.setLayoutProperty('secondary-roads', 'visibility', newVisible ? 'visible' : 'none');
    }
    
    // If turning on, ensure roads are on top
    if (newVisible) {
      bringWaterAndRoadsToTop(mapRef.current);
    }
  };

  // Function to toggle county animations
  const handleCountyAnimationsToggle = () => {
    if (!mapRef.current) return;
    
    const newVisible = !showCountyAnimations;
    setShowCountyAnimations(newVisible);
  };

  // Function to toggle UPS markers
  const handleUPSMarkersToggle = () => {
    if (!mapRef.current) return;
    
    const newVisible = !showUPSMarkers;
    setShowUPSMarkers(newVisible);
    
    // Toggle UPS marker visibility
    toggleUPSMarkers(mapRef.current, newVisible, mapboxglRef.current);
  };
  
  // Function to toggle Rail markers
  const handleRailMarkersToggle = () => {
    if (!mapRef.current) return;
    
    const newVisible = !showRailMarkers;
    setShowRailMarkers(newVisible);
    
    // Toggle rail marker visibility
    toggleRailMarkers(mapRef.current, newVisible, mapboxglRef.current);
  };

  // Function to toggle between metrics
  const handleMetricToggle = () => {
    if (!mapRef.current) return;

    // Remove any existing popups to prevent stale data
    if (hoverPopupRef.current) {
      hoverPopupRef.current.remove();
    }

    if (clickPopupRef.current) {
      clickPopupRef.current.remove();
    }

    // Toggle metric using utility function
    const newMetric = toggleMetricUtil(mapRef.current, currentMetricRef.current, is3D);
    
    // Update references and state
    currentMetricRef.current = newMetric;
    setCurrentMetric(newMetric);

    // Reorder layers
    setTimeout(() => {
      const layerOrdering = [...getLayerOrdering()];
      if (!layerOrdering.includes('county-extrusion-middle') && 
          layerOrdering.includes('county-extrusion-base')) {
        const baseIndex = layerOrdering.indexOf('county-extrusion-base');
        layerOrdering.splice(baseIndex + 1, 0, 'county-extrusion-middle');
      }
      orderLayers(mapRef.current, layerOrdering);
    }, 500);
  };

  // Function to toggle bivariate view
  const handleBivariateToggle = (showBivariate) => {
    if (!mapRef.current) return;

    // Remove any existing popups to prevent stale data
    if (hoverPopupRef.current) {
      hoverPopupRef.current.remove();
    }

    if (clickPopupRef.current) {
      clickPopupRef.current.remove();
    }

    // Set state
    setIsBivariateView(showBivariate);

    // Toggle visibility of layers
    toggleBivariateView(mapRef.current, is3D, showBivariate);

    // Reorder layers
    setTimeout(() => {
      const layerOrdering = [...getLayerOrdering()];
      // Add bivariate layers to ordering if needed
      if (!layerOrdering.includes('county-bivariate-fills')) {
        layerOrdering.push('county-bivariate-fills');
      }
      if (!layerOrdering.includes('county-bivariate-extrusions')) {
        layerOrdering.push('county-bivariate-extrusions');
      }
      orderLayers(mapRef.current, layerOrdering);
    }, 500);
  }; 

  // Function to toggle 3D view
  const handle3DToggle = () => {
    // Implement 3D toggle functionality
    setIs3D(!is3D);
  };

  // Function to toggle Amazon markers
  const handleAmazonMarkersToggle = () => {
    if (!mapRef.current) return;
    
    const newVisible = !showAmazonMarkers;
    setShowAmazonMarkers(newVisible);
    
    // Toggle marker visibility
    toggleAmazonMarkers(mapRef.current, newVisible);
  };

  useEffect(() => {
    // Dynamically import mapboxgl to avoid SSR issues
    const initializeMap = async () => {
      try {
        // Dynamically import mapboxgl
        const mapboxgl = await import('mapbox-gl');
        
        // Store in ref for use in other functions
        mapboxglRef.current = mapboxgl.default;
        
        // Setup map code goes here...
        
        // Add a timeout to ensure the map is loaded before adding rail markers
        setTimeout(async () => {
          if (mapRef.current) {
            console.log('Attempting to load rail facilities...');
            try {
              // Initialize rail markers
              const railMarkersAdded = await addRailFacilities(mapRef.current, mapboxgl.default);
              console.log('Rail markers added successfully:', railMarkersAdded);
              
              // Set initial visibility (hidden)
              toggleRailMarkers(mapRef.current, false, mapboxgl.default);
              
              // Debug
              console.log('--- DEBUG: Rail markers initialization completed ---');
              console.log('mapRef.current:', !!mapRef.current);
              console.log('mapboxglRef.current:', !!mapboxglRef.current);
              
              // After Amazon and UPS layers are added, log all layers again
              console.log('--- DEBUG: All map layers after rail markers ---');
              const mapLayers = mapRef.current.getStyle().layers || [];
              mapLayers.forEach(layer => {
                const visibility = mapRef.current.getLayoutProperty(layer.id, 'visibility') || 'default';
                console.log(`Layer: ${layer.id}, Type: ${layer.type}, Visible: ${visibility}`);
              });
              console.log('--- END DEBUG ---');
            } catch (error) {
              console.error('Error adding rail facilities:', error);
            }
          }
        }, 8000);
      } catch (error) {
        console.error('Error initializing map:', error);
      }
    };

    initializeMap();
  }, []);

  return (
    <div className="map-container">
      {loading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
        </div>
      )}
      <div
        ref={mapContainer}
        className="map"
      />

      {/* Direct Rail toggle button */}
      <button
        style={{
          position: 'fixed',
          bottom: '80px',
          left: '20px',
          zIndex: 1000,
          padding: '12px 20px',
          backgroundColor: showRailMarkers ? '#C71585' : '#333',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '16px'
        }}
        onClick={() => {
          console.log('Direct Rail button clicked, current state:', showRailMarkers);
          if (mapRef.current && mapboxglRef.current) {
            const newVisible = !showRailMarkers;
            setShowRailMarkers(newVisible);
            console.log('Toggling rail markers to:', newVisible);
            toggleRailMarkers(mapRef.current, newVisible, mapboxglRef.current);
            
            // List all layers again after toggle
            console.log('--- DEBUG: Layers after rail toggle ---');
            const mapLayers = mapRef.current.getStyle().layers || [];
            let railLayerFound = false;
            mapLayers.forEach(layer => {
              if (layer.id === 'rail-markers') {
                railLayerFound = true;
                const visibility = mapRef.current.getLayoutProperty(layer.id, 'visibility') || 'default';
                console.log(`RAIL LAYER FOUND: ${layer.id}, Visible: ${visibility}`);
              }
            });
            if (!railLayerFound) {
              console.log('RAIL LAYER NOT FOUND IN MAP LAYERS');
            }
            console.log('--- END DEBUG ---');
          }
        }}
      >
        {showRailMarkers ? 'Hide' : 'Show'} Rail (Direct)
      </button>

      {/* Add the RoadTraffic component for animated particles */}
      {mapRef.current && <RoadTraffic map={mapRef.current} />}

      {/* Map title */}
      <div id="map-title">
        Logistics Hub {isBivariateView ? 'Bivariate' : (currentMetric === 'obsolescence_score' ? 'Obsolescence' : 'Growth Potential')} Analysis
      </div>

      {/* Add the Legend component */}
      <Legend currentMetric={currentMetric} />

      {/* Direct placeholder button outside of MapControls */}
      <div style={{ 
        position: 'fixed', 
        left: '20px', 
        top: '200px', 
        zIndex: 9999 
      }}>
        <button
          style={{
            width: '180px',
            padding: '10px 15px',
            backgroundColor: '#FF00FF',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold',
            boxShadow: '0 0 10px rgba(0,0,0,0.5)'
          }}
          onClick={() => alert('Direct button clicked')}
        >
          RAIL BUTTON DIRECT
        </button>
      </div>

      {/* Add the MapControls component */}
      <MapControls
        is3D={is3D}
        toggle3D={handle3DToggle}
        currentMetric={currentMetric}
        toggleMetric={handleMetricToggle}
        isBivariateView={isBivariateView}
        toggleBivariateView={handleBivariateToggle}
        showAmazonMarkers={showAmazonMarkers}
        toggleAmazonMarkers={handleAmazonMarkersToggle}
        showCountyAnimations={showCountyAnimations}
        toggleCountyAnimations={handleCountyAnimationsToggle}
        showUPSMarkers={showUPSMarkers}
        toggleUPSMarkers={handleUPSMarkersToggle}
        showRailMarkers={showRailMarkers}
        toggleRailMarkers={handleRailMarkersToggle}
        showRoadLayer={showRoadLayer}
        toggleRoadLayer={handleRoadLayerToggle}
      />
    </div>
  );
};

export default MapComponent; 