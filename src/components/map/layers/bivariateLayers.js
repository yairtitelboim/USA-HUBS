/**
 * Bivariate Layer functions
 * These functions create and manage the bivariate visualization layers
 */

/**
 * Create a bivariate fill layer that visualizes both metrics simultaneously
 * @param {boolean} visible - Whether the layer should be visible initially
 * @returns {Object} The layer object to be added to the map
 */
export const createBivariateFillLayer = (visible = false) => {
  return {
    id: 'county-bivariate-fills',
    type: 'fill',
    source: 'counties',
    layout: {
      visibility: visible ? 'visible' : 'none'
    },
    paint: {
      'fill-color': [
        'interpolate',
        ['linear'],
        ['/', ['get', 'growth_potential_score'], ['get', 'obsolescence_score']],
        0, '#4575b4', // Low growth, high obsolescence: blue
        0.5, '#91bfdb', // Medium-low: light blue
        1, '#f7f7f7', // Balanced: white
        2, '#fc8d59', // Medium-high: orange
        4, '#d73027'  // High growth, low obsolescence: red
      ],
      'fill-opacity': 0.8,
      'fill-outline-color': '#000000'
    }
  };
};

/**
 * Create a 3D extrusion layer for bivariate visualization
 * @param {boolean} visible - Whether the layer should be visible initially
 * @returns {Object} The layer object to be added to the map
 */
export const createBivariateExtrusionLayer = (visible = false) => {
  return {
    id: 'county-bivariate-extrusions',
    type: 'fill-extrusion',
    source: 'counties',
    layout: {
      visibility: visible ? 'visible' : 'none'
    },
    paint: {
      'fill-extrusion-color': [
        'interpolate',
        ['linear'],
        ['/', ['get', 'growth_potential_score'], ['get', 'obsolescence_score']],
        0, '#4575b4', // Low growth, high obsolescence: blue
        0.5, '#91bfdb', // Medium-low: light blue
        1, '#f7f7f7', // Balanced: white
        2, '#fc8d59', // Medium-high: orange
        4, '#d73027'  // High growth, low obsolescence: red
      ],
      'fill-extrusion-height': [
        'interpolate',
        ['linear'],
        ['max', ['get', 'obsolescence_score'], ['get', 'growth_potential_score']],
        0, 0,
        100, 200000
      ],
      'fill-extrusion-base': 0,
      'fill-extrusion-opacity': 0.9
    }
  };
};

/**
 * Add bivariate layers to the map
 * @param {Object} map - The Mapbox map instance
 * @param {boolean} is3D - Whether to show the 3D or 2D version
 * @param {boolean} isVisible - Whether the layers should be visible
 */
export const addBivariateLayers = (map, is3D, isVisible) => {
  try {
    // Check if the map and counties source exist
    if (!map || !map.getSource('counties')) {
      console.error('Map or counties source not available for bivariate layers');
      return false;
    }

    // Check if the layers already exist
    const fillLayerExists = !!map.getLayer('county-bivariate-fills');
    const extrusionLayerExists = !!map.getLayer('county-bivariate-extrusions');

    if (fillLayerExists && extrusionLayerExists) {
      // Layers already exist, just update visibility
      map.setLayoutProperty(
        'county-bivariate-fills', 
        'visibility', 
        (!is3D && isVisible) ? 'visible' : 'none'
      );
      
      map.setLayoutProperty(
        'county-bivariate-extrusions', 
        'visibility', 
        (is3D && isVisible) ? 'visible' : 'none'
      );
    } else {
      // Layers don't exist, create them
      if (!fillLayerExists) {
        map.addLayer(createBivariateFillLayer(!is3D && isVisible));
      }
      
      if (!extrusionLayerExists) {
        map.addLayer(createBivariateExtrusionLayer(is3D && isVisible));
      }
    }

    return true;
  } catch (error) {
    console.error('Error adding bivariate layers:', error);
    return false;
  }
};

/**
 * Toggle bivariate view
 * @param {Object} map - The Mapbox map instance
 * @param {boolean} is3D - Whether to show the 3D or 2D version
 * @param {boolean} showBivariate - Whether to show the bivariate view
 */
export const toggleBivariateView = (map, is3D, showBivariate) => {
  try {
    // Hide standard layers
    const standardLayers = [
      'county-fills',
      'county-extrusions',
      'county-extrusion-base',
      'county-extrusion-middle',
      'county-extrusion-cap'
    ];

    standardLayers.forEach(layerId => {
      if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, 'visibility', showBivariate ? 'none' : 'visible');
      }
    });

    // Add or update bivariate layers
    addBivariateLayers(map, is3D, showBivariate);

    return showBivariate;
  } catch (error) {
    console.error('Error toggling bivariate view:', error);
    return false;
  }
}; 