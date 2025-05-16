import { addAmazonFulfillmentCenters, toggleAmazonMarkers } from './layers/amazonMarkers';

// Add this in the useEffect, after the line with setupPopupObserver()
// After line that looks like: observerRef.current = setupPopupObserver();
// Add Amazon fulfillment center markers
setTimeout(async () => {
  console.log('Adding Amazon fulfillment centers');
  // These variables need to be in scope when used in MapComponent.js
  // await addAmazonFulfillmentCenters(map, mapboxgl.default);
}, 3000);

// In the handleBivariateToggle function, add this after the call to toggleBivariateView:
// Toggle Amazon markers visibility based on bivariate mode
// Amazon markers are only visible in bivariate mode
// In MapComponent.js, these variables are available:
// map: from mapRef.current
// showBivariate: function parameter
// toggleAmazonMarkers(map, showBivariate); 