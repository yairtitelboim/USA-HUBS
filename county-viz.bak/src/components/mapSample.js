import React, { useRef, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import POIReviewPopup from './components/POIReviewPopup';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { askClaude, parseClaudeResponse } from '../../services/claude';
import { MapContainer, ToggleButton } from './styles/MapStyles';
import { Toggle3DButton, RotateButton } from './StyledComponents';
import AIChatPanel from './AIChatPanel/index';
import { useAIConsensusAnimation } from './hooks/useAIConsensusAnimation';
import { useMapInitialization } from './hooks/useMapInitialization';
import { PopupManager } from './components/PopupManager';
import { highlightPOIBuildings } from './utils';
import LayerToggle from './components/LayerToggle';
import { ErcotManager } from './components/ErcotManager';
import POIDataBar from './components/POIDataBar';
import POIData2 from './components/POIData2';
import POIGraph from './components/POIGraph';
import {
  initializeRoadParticles,
  animateRoadParticles,
  stopRoadParticles
} from './hooks/mapAnimations';
import ZoningLayer from './components/ZoningLayer';
import PlanningDocsLayer from './components/PlanningDocsLayer';
import PlanningAnalysisLayer from './components/PlanningAnalysisLayer';
import SceneManager from './components/SceneManager';
import LocalZonesLayer from './components/LocalZonesLayer';
import PropertyPricesLayer from './components/PropertyPricesLayer';
import EmploymentLayer from './components/EmploymentLayer';
import BostonBuildingsLayer from './components/BostonBuildingsLayer';
import POISynchronizer from './components/POISynchronizer';
import { getColorForCategory } from './utils/colorUtils';
import { initializeEventBus } from './utils/MapEventBus';
import { monitorPerformance, debugLog } from './utils/MapDebug';
import { setupMapInteractionHandlers, setupTouchHandlers } from './utils/MapInteractions';
import styled from 'styled-components';
import OSMPOILayer from './components/OSMPOILayer';
import CensusTractsLayer from './components/CensusTractsLayer';
import NetworkMarkers from './components/NetworkMarkers';
import PermitsLayer from './components/PermitsLayer';
import PermitsMarkerLayer from './components/PermitsMarkerLayer';
import StaticPermitCensusLayer from './components/StaticPermitCensusLayer';
import CityBudgetLayer from './components/CityBudgetLayer';
import LLMReviewLayer from './components/LLMReviewLayer';
import './components/LLMReviewPopup.css'; // Import the LLM Review popup styles


// Set mapbox access token
mapboxgl.accessToken = process.env.REACT_APP_MAPBOX_ACCESS_TOKEN;

// Initialize event bus
initializeEventBus();

// Add styled components for the popup
const StyledPopup = styled.div`
  .mapboxgl-popup-content {
    padding: 15px;
    border-radius: 8px;
    background: rgba(0, 0, 0, 0.85);
    color: white;
    font-family: 'SF Mono', monospace;
    font-size: 14px;
    line-height: 1.4;
    min-width: 200px;
  }

  .mapboxgl-popup-close-button {
    color: white;
    font-size: 16px;
    padding: 4px 8px;
    right: 4px;
    top: 4px;
  }

  .poi-popup-content {
    h3 {
      margin: 0 0 8px 0;
      color: white;
      font-size: 16px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .poi-details {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.8);
      margin-top: 12px;
      padding-left: 8px;
      border-left: 2px solid rgba(76, 175, 80, 0.5);
    }

    .poi-meta {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-top: 8px;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.6);
    }
  }
`;

const MapComponent = () => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const roadAnimationFrame = useRef(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('Processing...');
  const [inputValue, setInputValue] = useState('');
  const [isErcotMode, setIsErcotMode] = useState(false);
  const [showRoadParticles, setShowRoadParticles] = useState(true);
  const [is3DActive, setIs3DActive] = useState(false);
  const [currentRotation, setCurrentRotation] = useState(0);
  const roadParticleAnimation = useRef(null);
  const [showZoningLayer, setShowZoningLayer] = useState(false);
  const [showPlanningDocsLayer, setShowPlanningDocsLayer] = useState(false);
  const [showPlanningAnalysis, setShowPlanningAnalysis] = useState(false);
  const [showAdaptiveReuse, setShowAdaptiveReuse] = useState(false);
  const [showDevelopmentPotential, setShowDevelopmentPotential] = useState(false);
  const [showTransportation, setShowTransportation] = useState(false);
  const [is3DLoading, setIs3DLoading] = useState(false);
  const [showPropertyPrices, setShowPropertyPrices] = useState(false);
  const [showEmployment, setShowEmployment] = useState(false);
  const [showLocalZones, setShowLocalZones] = useState(false);
  const [showLocalZoneBoundaries, setShowLocalZoneBoundaries] = useState(false);
  const [showLocalZoneLabels, setShowLocalZoneLabels] = useState(false);
  const [showParks, setShowParks] = useState(false); // Parks toggle is off by default
  const [isLayerMenuCollapsed, setIsLayerMenuCollapsed] = useState(true);
  const [showPOIMarkers, setShowPOIMarkers] = useState(false);
  const [showOSMPOIs, setShowOSMPOIs] = useState(false);
  const [poiLayerInitialized, setPoiLayerInitialized] = useState(false);
  const [graphOnlyMode, setGraphOnlyMode] = useState(false);
  const [selectedPOI, setSelectedPOI] = useState(null);
  const [poiGraphVisible, setPoiGraphVisible] = useState(false);
  const [showBostonBuildings, setShowBostonBuildings] = useState(false);
  const [showCensusTracts, setShowCensusTracts] = useState(false);
  const [showNetworkLayer, setShowNetworkLayer] = useState(false);
  const [useRoadPaths, setUseRoadPaths] = useState(true);
  const [showPermits, setShowPermits] = useState(false);
  const [showNewPermits, setShowNewPermits] = useState(false);
  const [showPermitCensus, setShowPermitCensus] = useState(false);
  const [showCityBudget, setShowCityBudget] = useState(false);
  const [showLLMReview, setShowLLMReview] = useState(false);
  const [selectedPolygonId, setSelectedPolygonId] = useState(null);
  const [categoryVisibility, setCategoryVisibility] = useState({});
  const [isSceneSidebarOpen, setIsSceneSidebarOpen] = useState(false);
  const [showPOIData2, setShowPOIData2] = useState(false);

  const ercotManagerRef = useRef(null);
  const poiDataBarRef = useRef(null);
  const poiData2Ref = useRef(null);

  // Initialize map and AI consensus animation
  const { initializeParticleLayer } = useAIConsensusAnimation(map, false);
  useMapInitialization(map, mapContainer);

  // Start performance monitoring
  useEffect(() => {
    debugLog('Map component mounted');
    const cleanup = monitorPerformance();
    return () => {
      debugLog('Map component unmounted');
      if (cleanup) cleanup();
    };
  }, []);

  // Set up map interaction handlers
  useEffect(() => {
    if (!map.current) return;
    const cleanup = setupMapInteractionHandlers(map.current);
    return cleanup;
  }, []);

  // Set up touch handlers
  useEffect(() => {
    if (!map.current) return;
    const cleanup = setupTouchHandlers(map.current);
    return cleanup;
  }, []);

  // Initialize POI layer
  useEffect(() => {
    if (!map.current || poiLayerInitialized) return;

    const initializePOILayer = () => {
      try {
        // Add POI layer from Mapbox tiles
        map.current.addLayer({
          'id': 'miami-pois',
          'type': 'circle',
          'source': 'composite',
          'source-layer': 'poi_label',
          'minzoom': 0,
          'maxzoom': 22,
          'paint': {
            'circle-radius': [
              'interpolate',
              ['linear'],
              ['zoom'],
              8, 1.3,
              12, 2.6,
              16, 3.9
            ],
            'circle-color': [
              'match',
              ['get', 'type'],
              'Restaurant', '#ff9900',
              'Cafe', '#cc6600',
              'Bar', '#990099',
              'Fast Food', '#ff6600',
              'Shop', '#0066ff',
              'Grocery', '#00cc00',
              'Mall', '#3366ff',
              'Market', '#009933',
              'Museum', '#cc3300',
              'Theater', '#cc0066',
              'Cinema', '#990033',
              'Gallery', '#cc3366',
              'Park', '#33cc33',
              'Garden', '#339933',
              'Sports', '#3399ff',
              'Hotel', '#9933ff',
              'Bank', '#666699',
              'Post', '#666666',
              'School', '#ff3333',
              'Hospital', '#ff0000',
              '#999999'  // Default color for unmatched types
            ],
            'circle-stroke-width': [
              'interpolate',
              ['linear'],
              ['zoom'],
              8, 0.5,
              12, 1,
              16, 1.5
            ],
            'circle-stroke-color': '#ffffff'
          }
        });

        // Add hover effects
        map.current.on('mouseenter', 'miami-pois', () => {
          map.current.getCanvas().style.cursor = 'pointer';
        });

        map.current.on('mouseleave', 'miami-pois', () => {
          map.current.getCanvas().style.cursor = '';
        });

        // Add click handler with popup
        map.current.on('click', 'miami-pois', (e) => {
          if (!e.features[0]) return;

          const poiCoordinates = e.features[0].geometry.coordinates;
          const properties = e.features[0].properties;

          console.log('Map: POI marker clicked:', {
            coordinates: poiCoordinates,
            properties: properties,
            feature: e.features[0]
          });

          // Emit event for graph to handle POI selection with more details
          window.mapEventBus.emit('marker:selected', {
            coordinates: poiCoordinates,
            properties: {
              name: properties.name,
              type: properties.type,
              lngLat: poiCoordinates,
              source: 'mapbox'
            },
            feature: e.features[0]
          });

          // Create popup content with React component
          const popupContent = document.createElement('div');
          popupContent.className = 'poi-popup-content';

          // Create a feature object with the structure expected by POIReviewPopup
          const feature = {
            geometry: {
              coordinates: poiCoordinates
            },
            properties: {
              ...properties,
              // Add color based on category
              color: getColorForCategory(properties.type || properties.class || 'default'),
              // Add mock reviews since Mapbox POIs don't have reviews
              reviews: [
                {
                  author_name: 'Local Guide',
                  rating: 4,
                  relative_time_description: '2 months ago',
                  text: 'Great place! The atmosphere is wonderful and the service is excellent.'
                },
                {
                  author_name: 'Visitor',
                  rating: 5,
                  relative_time_description: '3 weeks ago',
                  text: 'One of my favorite spots in the area. Highly recommended!'
                },
                {
                  author_name: 'Resident',
                  rating: 3,
                  relative_time_description: '1 month ago',
                  text: 'Decent place. Could improve on a few things but overall a good experience.'
                }
              ],
              // Add rating if not present
              rating: properties.rating || 4.0,
              review_count: properties.review_count || 3
            }
          };

          // Render our React component into the popup content
          const root = createRoot(popupContent);
          root.render(<POIReviewPopup feature={feature} />);

          // Create and add popup
          new mapboxgl.Popup({
            offset: [0, -5],
            closeButton: true,
            closeOnClick: true,
            maxWidth: '320px'
          })
            .setLngLat(poiCoordinates)
            .setDOMContent(popupContent)
            .addTo(map.current);

          // Fly to the POI
          map.current.flyTo({
            center: poiCoordinates,
            zoom: Math.min(map.current.getZoom() + 1, 16),
            duration: 1000
          });
        });

        setPoiLayerInitialized(true);
      } catch (error) {
        console.error('Error initializing POI layer:', error);
      }
    };

    if (map.current.loaded()) {
      initializePOILayer();
    } else {
      map.current.once('load', initializePOILayer);
    }
  }, [map, poiLayerInitialized]);

  // Handle POI layer visibility
  useEffect(() => {
    if (!map.current || !poiLayerInitialized) return;

    map.current.setLayoutProperty(
      'miami-pois',
      'visibility',
      showPOIMarkers ? 'visible' : 'none'
    );
  }, [showPOIMarkers, poiLayerInitialized]);

  // Handle road particles animation
  useEffect(() => {
    if (!map.current) return;

    const initializeParticles = async () => {
      if (showRoadParticles) {
        debugLog('Starting road particles animation...');
        initializeRoadParticles(map.current);

        const animate = (timestamp) => {
          if (!map.current) return;
          animateRoadParticles({ map: map.current, timestamp });
          roadParticleAnimation.current = requestAnimationFrame(animate);
        };

        roadParticleAnimation.current = requestAnimationFrame(animate);
      } else {
        if (roadParticleAnimation.current) {
          stopRoadParticles(map.current);
          cancelAnimationFrame(roadParticleAnimation.current);
          roadParticleAnimation.current = null;
        }
      }
    };

    if (map.current.loaded()) {
      initializeParticles();
    } else {
      map.current.once('load', initializeParticles);
    }

    return () => {
      if (roadParticleAnimation.current) {
        cancelAnimationFrame(roadParticleAnimation.current);
        roadParticleAnimation.current = null;
      }
    };
  }, [showRoadParticles]);

  // Handle POI selection from graph
  useEffect(() => {
    if (!map.current) return;

    console.log('Map: Setting up POI selection handler');

    const handlePOISelection = (event) => {
      console.log('Map: Received POI selection event:', event);

      const { coordinates, properties, source } = event;

      // Skip creating a popup if the event came from the POI Graph
      // The POI Graph now creates its own popup
      if (source === 'poigraph') {
        console.log('Map: Skipping popup creation for POI Graph selection');
        return;
      }

      // Find the POI marker at the coordinates
      const features = map.current.queryRenderedFeatures(undefined, {
        layers: ['miami-pois']
      });

      console.log('Map: Found features:', {
        count: features.length,
        features: features.map(f => ({
          name: f.properties.name,
          coordinates: f.geometry.coordinates,
          type: f.properties.type
        }))
      });

      // Find the matching feature
      const matchingFeature = features.find(feature => {
        const featureCoords = feature.geometry.coordinates;
        const matches = Math.abs(featureCoords[0] - coordinates[0]) < 0.0001 &&
                       Math.abs(featureCoords[1] - coordinates[1]) < 0.0001;

        console.log('Map: Checking feature match:', {
          featureName: feature.properties.name,
          featureCoords,
          targetCoords: coordinates,
          matches
        });

        return matches;
      });

      if (matchingFeature) {
        console.log('Map: Found matching feature:', matchingFeature);

        // Highlight the marker by temporarily increasing its size
        map.current.setPaintProperty('miami-pois', 'circle-radius', [
          'case',
          ['==', ['get', 'name'], properties.name],
          ['interpolate', ['linear'], ['zoom'],
            8, 3,
            12, 4,
            16, 5
          ],
          ['interpolate', ['linear'], ['zoom'],
            8, 1.3,
            12, 2.6,
            16, 3.9
          ]
        ]);

        // Reset the highlight after 2 seconds
        setTimeout(() => {
          console.log('Map: Resetting POI highlight');
          map.current.setPaintProperty('miami-pois', 'circle-radius', [
            'interpolate', ['linear'], ['zoom'],
              8, 1.3,
              12, 2.6,
              16, 3.9
          ]);
        }, 2000);
      } else {
        console.log('Map: No matching feature found for coordinates:', coordinates);
      }

      // Create popup content with React component
      const popupContent = document.createElement('div');
      popupContent.className = 'poi-popup-content';

      // Create a feature object with the structure expected by POIReviewPopup
      const featureObj = {
        geometry: {
          coordinates: coordinates
        },
        properties: {
          ...properties,
          // Add color based on category
          color: getColorForCategory(properties.type || properties.category || 'default'),
          // Add mock reviews since these POIs might not have reviews
          reviews: [
            {
              author_name: 'Local Guide',
              rating: 4,
              relative_time_description: '2 months ago',
              text: 'Great place! The atmosphere is wonderful and the service is excellent.'
            },
            {
              author_name: 'Visitor',
              rating: 5,
              relative_time_description: '3 weeks ago',
              text: 'One of my favorite spots in the area. Highly recommended!'
            },
            {
              author_name: 'Resident',
              rating: 3,
              relative_time_description: '1 month ago',
              text: 'Decent place. Could improve on a few things but overall a good experience.'
            }
          ],
          // Add rating if not present
          rating: properties.rating || 4.0,
          review_count: properties.review_count || 3
        }
      };

      // Render our React component into the popup content
      const root = createRoot(popupContent);
      root.render(<POIReviewPopup feature={featureObj} />);

      // Create a popup with an offset to move it up
      new mapboxgl.Popup({
        offset: [0, -5],
        closeButton: true,
        closeOnClick: true,
        maxWidth: '320px',
        className: 'poi-popup-custom'
      })
        .setLngLat(coordinates)
        .setDOMContent(popupContent)
        .addTo(map.current);

      // Add custom style for this popup type if it doesn't exist
      if (!document.getElementById('poi-popup-custom-style')) {
        const style = document.createElement('style');
        style.id = 'poi-popup-custom-style';
        style.innerHTML = `
          .poi-popup-custom .mapboxgl-popup-content {
            background-color: transparent !important;
            padding: 0 !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
          }
          .poi-popup-custom .mapboxgl-popup-tip {
            display: none;
          }
          .poi-popup-content {
            padding: 12px;
            border-radius: 8px;
          }
        `;
        document.head.appendChild(style);
      }
    };

    // Listen for POI selection events and store the unsubscribe function
    const unsubscribe = window.mapEventBus.on('poi:selected', handlePOISelection);
    console.log('Map: POI selection handler set up');

    // Cleanup using the unsubscribe function
    return () => {
      console.log('Map: Cleaning up POI selection handler');
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
  }, [map]);

  // Handle POI Graph visibility changes
  useEffect(() => {
    const unsubscribe = window.mapEventBus.on('poigraph:visibility', (event) => {
      console.log('Map: POI Graph visibility changed:', event);
      setPoiGraphVisible(event.isVisible);

      // Trigger a map resize after the transition
      setTimeout(() => {
        if (map.current) {
          map.current.resize();
          console.log('Map: Resized after POI Graph visibility change');
        }
      }, 300); // Match the transition duration
    });

    return () => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
  }, []);

  // Listen for POI selection events
  useEffect(() => {
    if (!window.mapEventBus) return;

    console.log('Map: Setting up POI selection event listener');

    const unsubscribe = window.mapEventBus.on('poi:selected', (event) => {
      console.log('Map: POI selected event received:', event);
      setSelectedPOI(event);

      // Clear the selection after 5 seconds
      setTimeout(() => {
        setSelectedPOI(null);
      }, 5000);
    });

    return () => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
  }, []);

  // Add handler for category visibility changes from POI Graph
  useEffect(() => {
    if (!window.mapEventBus) return;

    console.log('Map: Setting up category visibility handler');

    const unsubscribe = window.mapEventBus.on('poigraph:categoryVisibility', (event) => {
      console.log('Map: Received category visibility update:', event);
      setCategoryVisibility(event.categories);
    });

    return () => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
  }, []);

  // Add logging for BostonBuildingsLayer props
  useEffect(() => {
    console.log('Map: BostonBuildingsLayer props updated:', {
      visible: showBostonBuildings,
      selectedPOI: selectedPolygonId,
      visibleCategories: categoryVisibility
    });
  }, [showBostonBuildings, selectedPolygonId, categoryVisibility]);

  // Listen for POIData2 visibility events from POI Graph
  useEffect(() => {
    if (!window.mapEventBus) return;

    console.log('Map: Setting up POIData2 visibility event listener');

    const unsubscribe = window.mapEventBus.on('poigraph:show_poi_data2', (event) => {
      console.log('Map: Received request to show POIData2:', event);
      if (event.show) {
        setShowPOIData2(true);
      }
    });

    return () => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
  }, []);

  const handleQuestion = async (question) => {
    window.mapEventBus.emit('ai:processing');
    setIsLoading(true);
    setMessages(prev => [...prev, { isUser: true, content: question }]);

    try {
      const bounds = map.current.getBounds();
      const mapBounds = {
        sw: bounds.getSouthWest(),
        ne: bounds.getNorthEast()
      };

      const response = await askClaude(question, {}, mapBounds);
      const parsedResponse = parseClaudeResponse(response);

      if (parsedResponse.mainText !== "Could not process the response. Please try again.") {
        setMessages(prev => [...prev, {
          isUser: false,
          content: parsedResponse
        }]);
        handleLLMResponse(parsedResponse);
      } else {
        throw new Error('Failed to parse response');
      }
    } catch (error) {
      console.error('Error in handleQuestion:', error);
      setMessages(prev => [...prev, {
        isUser: false,
        content: {
          mainText: "I apologize, but I encountered an error processing your request. Please try asking your question again.",
          poiInfo: null,
          followUps: []
        }
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLLMResponse = (response) => {
    if (!map.current) return;

    if (response?.coordinates) {
      map.current.flyTo({
        center: response.coordinates,
        zoom: response.zoomLevel,
        duration: 1000
      });

      map.current.once('moveend', () => {
        map.current.once('idle', () => {
          // Highlight POIs with improved visibility
          highlightPOIBuildings(map.current, ['restaurant', 'bar', 'nightclub'], '#FF4500');
          console.log('🏢 Applied large, visible highlights to POIs');

          // Optionally hide the standard POI markers for cleaner visualization
          if (map.current) {
            map.current.setLayoutProperty('miami-pois', 'visibility', 'none');
          }
        });
      });
    }
  };

  const rotateMap = () => {
    if (!map.current) return;
    const newRotation = (currentRotation + 90) % 360;
    map.current.easeTo({
      bearing: newRotation,
      duration: 1000
    });
    setCurrentRotation(newRotation);
  };

  const handlePOIClick = (e) => {
    const feature = e.features[0];
    if (!feature) return;

    const coordinates = feature.geometry.coordinates.slice();
    const properties = feature.properties;

    console.log('Map: OSM POI clicked:', {
      coordinates: coordinates,
      properties: properties,
      feature: feature
    });

    // Emit event for graph to handle POI selection
    window.mapEventBus.emit('marker:selected', {
      coordinates: coordinates,
      properties: {
        name: properties.name,
        type: properties.type || properties.class,
        lngLat: coordinates,
        source: 'osm'
      },
      feature: feature
    });

    // Create popup content with React component
    const popupContent = document.createElement('div');
    popupContent.className = 'osm-poi-popup';

    // Render our React component into the popup content
    const root = createRoot(popupContent);
    root.render(<POIReviewPopup feature={feature} />);

    // Create and show popup
    new mapboxgl.Popup({
      offset: [0, -5],
      closeButton: true,
      closeOnClick: true,
      maxWidth: '320px'
    })
      .setLngLat(coordinates)
      .setDOMContent(popupContent)
      .addTo(map.current);

    // Fly to the POI
    map.current.flyTo({
      center: coordinates,
      zoom: 16,
      duration: 2000
    });
  };

  return (
    <MapContainer $poiGraphVisible={poiGraphVisible}>
      <div
        ref={mapContainer}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: poiGraphVisible ? '45%' : 0,
          transition: 'bottom 0.3s ease-in-out'
        }}
      />

      <PopupManager map={map} />
      <POISynchronizer map={map.current} poiDataBarRef={poiDataBarRef} poiData2Ref={poiData2Ref} />
      <ErcotManager ref={ercotManagerRef} map={map} isErcotMode={isErcotMode} setIsErcotMode={setIsErcotMode} />
      <POIDataBar
        ref={poiDataBarRef}
        map={map}
        showOSMPOIs={showOSMPOIs}
        setShowOSMPOIs={setShowOSMPOIs}
        showPOIMarkers={showPOIMarkers}
        setShowPOIMarkers={setShowPOIMarkers}
      />

      {/* POIData2 component with visible prop */}
      <POIData2
        ref={poiData2Ref}
        map={map}
        showOSMPOIs={showOSMPOIs}
        setShowOSMPOIs={setShowOSMPOIs}
        showPOIMarkers={showPOIMarkers}
        setShowPOIMarkers={setShowPOIMarkers}
        visible={showPOIData2}
      />

      {/* Toggle button for POIData2 removed */}

      <POIGraph
        map={map}
        showPOIMarkers={showPOIMarkers}
        setShowPOIMarkers={setShowPOIMarkers}
        showOSMPOIs={showOSMPOIs}
        setShowOSMPOIs={setShowOSMPOIs}
        graphOnlyMode={graphOnlyMode}
        setGraphOnlyMode={setGraphOnlyMode}
        poiDataBarRef={poiDataBarRef}
      />

      <LayerToggle
        map={map}
        isLayerMenuCollapsed={isLayerMenuCollapsed}
        setIsLayerMenuCollapsed={setIsLayerMenuCollapsed}
        showZoningLayer={showZoningLayer}
        setShowZoningLayer={setShowZoningLayer}
        showPlanningAnalysis={showPlanningAnalysis}
        setShowPlanningAnalysis={setShowPlanningAnalysis}
        showAdaptiveReuse={showAdaptiveReuse}
        setShowAdaptiveReuse={setShowAdaptiveReuse}
        showDevelopmentPotential={showDevelopmentPotential}
        setShowDevelopmentPotential={setShowDevelopmentPotential}
        showTransportation={showTransportation}
        setShowTransportation={setShowTransportation}
        is3DLoading={is3DLoading}
        setIs3DLoading={setIs3DLoading}
        showPropertyPrices={showPropertyPrices}
        setShowPropertyPrices={setShowPropertyPrices}
        showEmployment={showEmployment}
        setShowEmployment={setShowEmployment}
        showLocalZones={showLocalZones}
        setShowLocalZones={setShowLocalZones}
        showLocalZoneBoundaries={showLocalZoneBoundaries}
        setShowLocalZoneBoundaries={setShowLocalZoneBoundaries}
        showLocalZoneLabels={showLocalZoneLabels}
        setShowLocalZoneLabels={setShowLocalZoneLabels}
        showPOIMarkers={showPOIMarkers}
        setShowPOIMarkers={setShowPOIMarkers}
        showOSMPOIs={showOSMPOIs}
        setShowOSMPOIs={setShowOSMPOIs}
        showBostonBuildings={showBostonBuildings}
        setShowBostonBuildings={setShowBostonBuildings}
        showParks={showParks}
        setShowParks={setShowParks}
        showCensusTracts={showCensusTracts}
        setShowCensusTracts={setShowCensusTracts}
        showNetworkLayer={showNetworkLayer}
        setShowNetworkLayer={setShowNetworkLayer}
        useRoadPaths={useRoadPaths}
        setUseRoadPaths={setUseRoadPaths}
        isSceneSidebarOpen={isSceneSidebarOpen}
        setIsSceneSidebarOpen={setIsSceneSidebarOpen}
        showPermits={showPermits}
        setShowPermits={setShowPermits}
        showNewPermits={showNewPermits}
        setShowNewPermits={setShowNewPermits}
        showPermitCensus={showPermitCensus}
        setShowPermitCensus={setShowPermitCensus}
        showCityBudget={showCityBudget}
        setShowCityBudget={setShowCityBudget}
        showLLMReview={showLLMReview}
        setShowLLMReview={setShowLLMReview}
      />

      <OSMPOILayer
        map={map}
        visible={showOSMPOIs}
        onPOIClick={handlePOIClick}
      />

      {/* BostonBuildingsLayer component */}
      <BostonBuildingsLayer
        map={map}
        visible={showBostonBuildings}
        selectedPOI={selectedPolygonId}
        visibleCategories={categoryVisibility}
      />

      <ToggleButton
        $active={showRoadParticles}
        onClick={() => setShowRoadParticles(!showRoadParticles)}
        style={{ height: '32px', padding: '0 12px', fontSize: '14px', marginBottom: '8px' }}
      >
        {showRoadParticles ? 'Hide Flow' : 'Show Flow'}
      </ToggleButton>

      <Toggle3DButton
        $active={is3DActive}
        onClick={() => setIs3DActive(!is3DActive)}
        disabled={is3DLoading}
        aria-label="Toggle 3D view"
      >
        {is3DLoading ? '...' : (is3DActive ? '2D' : '3D')}
      </Toggle3DButton>

      <RotateButton
        onClick={rotateMap}
        aria-label="Rotate map"
      >
        ↻
      </RotateButton>

      <ToggleButton
        $active={isSceneSidebarOpen}
        onClick={() => setIsSceneSidebarOpen(!isSceneSidebarOpen)}
        style={{
          height: '32px',
          padding: '0 12px',
          fontSize: '14px',
          marginBottom: '8px',
          position: 'absolute',
          bottom: '10px',
          right: '10px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h-4.5m-9 0H5a2 2 0 01-2-2V7a2 2 0 012-2h1.5m9 0h4.5a2 2 0 012 2v.5M9 7h1m5 0h1M9 11h1m5 0h1M9 15h1m5 0h1M9 19h1m5 0h1" />
        </svg>
        Scenes
      </ToggleButton>

      <AIChatPanel
        messages={messages}
        setMessages={setMessages}
        isLoading={isLoading}
        loadingMessage={loadingMessage}
        inputValue={inputValue}
        setInputValue={setInputValue}
        map={map.current}
        handleQuestion={handleQuestion}
        initialCollapsed={true}
      />

      {showZoningLayer && <ZoningLayer map={map} visible={showZoningLayer} />}
      {showPlanningDocsLayer && <PlanningDocsLayer map={map} visible={showPlanningDocsLayer} />}
      {showPlanningAnalysis && (
        <PlanningAnalysisLayer
          map={map}
          showAdaptiveReuse={showAdaptiveReuse}
          showDevelopmentPotential={showDevelopmentPotential}
        />
      )}
      {showPropertyPrices && <PropertyPricesLayer map={map} showPropertyPrices={showPropertyPrices} />}
      {showEmployment && <EmploymentLayer map={map} showEmployment={showEmployment} />}
      {showLocalZones && (
        <LocalZonesLayer
          map={map}
          showLocalZones={showLocalZones}
          showLocalZoneBoundaries={showLocalZoneBoundaries}
          showLocalZoneLabels={showLocalZoneLabels}
        />
      )}

      {/* Census Tracts Layer */}
      <CensusTractsLayer
        map={map}
        visible={showCensusTracts}
      />

      {/* Network Analysis Layer */}
      <NetworkMarkers
        map={map}
        visible={showNetworkLayer}
      />

      {/* Old Permits Layer */}
      <PermitsLayer
        map={map}
        visible={showPermits}
      />

      {/* New Permits Layer */}
      <PermitsMarkerLayer
        map={map}
        visible={showNewPermits}
      />

      {/* Permit Census Layer */}
      <StaticPermitCensusLayer
        map={map}
        visible={showPermitCensus}
      />

      {/* City Budget Layer */}
      <CityBudgetLayer
        map={map}
        visible={showCityBudget}
      />

      {/* LLM Review Layer */}
      <LLMReviewLayer
        map={map}
        visible={showLLMReview}
      />

      {map.current && (
        <SceneManager
          map={map.current}
          isOpen={isSceneSidebarOpen}
          onClose={() => setIsSceneSidebarOpen(false)}
        />
      )}


    </MapContainer>
  );
};

export default MapComponent;
