import React, { useEffect } from 'react';
import './MapControls.css';

/**
 * Map controls component for toggling between different visualization modes
 */
const MapControls = ({
  is3D,
  toggle3D,
  currentMetric,
  toggleMetric,
  isCombinedView = false, // Default to false if undefined
  isBivariateView = false, // Default to false for bivariate view
  toggleBivariateView,
  showAmazonMarkers = false,
  toggleAmazonMarkers,
  showCountyAnimations = false,
  toggleCountyAnimations,
  showUPSMarkers = false,
  toggleUPSMarkers,
  showRailMarkers = false,
  toggleRailMarkers,
  showRoadLayer = true, // Default to true for road layer
  toggleRoadLayer
}) => {
  const isObsolescence = currentMetric === 'obsolescence_score';

  // Log prop values when they change
  useEffect(() => {
    console.log("MapControls received props update:", {
      is3D,
      currentMetric,
      isCombinedView,
      isBivariateView,
      showAmazonMarkers,
      showCountyAnimations,
      showUPSMarkers,
      showRailMarkers
    });

    // Set the initial clicked state based on the current metric
    setTimeout(() => {
      const buttons = document.querySelectorAll('.metric-button');
      buttons.forEach(btn => btn.classList.remove('clicked'));

      if (isBivariateView) {
        document.getElementById('bivariate-button')?.classList.add('clicked');
      } else if (isCombinedView) {
        document.getElementById('combined-view-button')?.classList.add('clicked');
      } else if (currentMetric === 'obsolescence_score') {
        document.getElementById('obsolescence-button')?.classList.add('clicked');
      } else if (currentMetric === 'growth_potential_score') {
        // Default to the Growth button for growth_potential_score
        document.getElementById('growth-button')?.classList.add('clicked');
      }
    }, 100);
  }, [is3D, currentMetric, isCombinedView, isBivariateView, showAmazonMarkers, showCountyAnimations, showUPSMarkers, showRailMarkers]);

  // Handle direct button clicks without relying on toggleCombinedView
  const handleObsolescenceClick = () => {
    console.log("Obsolescence button clicked");
    // If in combined view, we need special handling
    if (isCombinedView) {
      console.log("Need to exit combined view and show obsolescence");
      // Dispatch a custom event to exit combined view
      window.dispatchEvent(new CustomEvent('toggleCombinedView', {detail: false}));

      // Make sure we're showing obsolescence
      if (!isObsolescence) {
        // Use setTimeout to ensure the combined view toggle has completed
        setTimeout(() => {
          toggleMetric('obsolescence_score');
        }, 50);
      }
    } else if (isBivariateView) {
      // Exit bivariate view
      toggleBivariateView(false);
      
      // Switch to obsolescence if needed
      if (!isObsolescence) {
        toggleMetric('obsolescence_score');
      }
    } else if (!isObsolescence) {
      // If not already showing obsolescence, switch to it
      toggleMetric('obsolescence_score');
    }
  };

  const handleGrowthClick = () => {
    console.log("Growth button clicked");
    // If in combined view, we need special handling
    if (isCombinedView) {
      console.log("Need to exit combined view and show growth");
      // Dispatch a custom event to exit combined view
      window.dispatchEvent(new CustomEvent('toggleCombinedView', {detail: false}));

      // Make sure we're showing growth
      if (isObsolescence) {
        // Use setTimeout to ensure the combined view toggle has completed
        setTimeout(() => {
          toggleMetric('growth_potential_score');
        }, 50);
      }
    } else if (isBivariateView) {
      // Exit bivariate view
      toggleBivariateView(false);
      
      // Switch to growth if needed
      if (isObsolescence) {
        toggleMetric('growth_potential_score');
      }
    } else if (isObsolescence) {
      // If already showing obsolescence, switch to growth
      toggleMetric('growth_potential_score');
    }
  };

  const handleBivariateClick = () => {
    console.log("Bivariate button clicked");
    if (!isBivariateView) {
      toggleBivariateView(true);
    }
  };

  return (
    <>
      {/* 3D/2D toggle button - now positioned outside the main container */}
      <button
        id="toggle3D"
        type="button"
        onClick={toggle3D}
      >
        Switch to {is3D ? '2D' : '3D'} View
      </button>

      {/* Standalone Rail toggle button for testing */}
      <button
        id="standalonRailToggle"
        type="button"
        onClick={toggleRailMarkers}
        style={{
          position: 'fixed',
          bottom: '20px',
          left: '20px',
          zIndex: 1000,
          padding: '10px 15px',
          backgroundColor: showRailMarkers ? '#C71585' : '#333',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        {showRailMarkers ? 'Hide' : 'Show'} Rail (Test)
      </button>

      {/* Main controls container with metric buttons */}
      <div className="map-controls">
        {/* Metric toggle buttons */}
        <div className="metric-toggle-buttons">
          <button
            className={`metric-button ${isObsolescence && !isCombinedView && !isBivariateView ? 'active' : ''}`}
            onClick={(e) => {
              // Add a clicked class to track which button was clicked last
              document.querySelectorAll('.metric-button').forEach(btn => btn.classList.remove('clicked'));
              e.currentTarget.classList.add('clicked');
              handleObsolescenceClick();
            }}
            id="obsolescence-button"
          >
            Obsolescence
          </button>

          <button
            className={`metric-button ${!isObsolescence && !isCombinedView && !isBivariateView && currentMetric === 'growth_potential_score' ? 'active' : ''}`}
            onClick={(e) => {
              // Add a clicked class to track which button was clicked last
              document.querySelectorAll('.metric-button').forEach(btn => btn.classList.remove('clicked'));
              e.currentTarget.classList.add('clicked');
              handleGrowthClick();
            }}
            id="growth-button"
          >
            Growth
          </button>
          
          <button
            className={`metric-button ${isBivariateView ? 'active' : ''}`}
            onClick={(e) => {
              // Add a clicked class to track which button was clicked last
              document.querySelectorAll('.metric-button').forEach(btn => btn.classList.remove('clicked'));
              e.currentTarget.classList.add('clicked');
              handleBivariateClick();
            }}
            id="bivariate-button"
          >
            Bivariate
          </button>
        </div>
        
        {/* Data layer toggle buttons */}
        <div className="toggle-controls">
          {/* Amazon fulfillment centers toggle button */}
          <button
            id="toggleAmazon"
            type="button"
            onClick={toggleAmazonMarkers}
            className={`toggle-button ${showAmazonMarkers ? 'amazon-active' : ''}`}
          >
            {showAmazonMarkers ? 'Hide' : 'Show'} Amazon
          </button>
          
          {/* UPS facilities toggle button */}
          <button
            id="toggleUPS"
            type="button"
            onClick={toggleUPSMarkers}
            className={`toggle-button ${showUPSMarkers ? 'ups-active' : ''}`}
          >
            {showUPSMarkers ? 'Hide' : 'Show'} UPS
          </button>
          
          {/* Rail facilities toggle button */}
          <button
            id="toggleRail"
            type="button"
            onClick={toggleRailMarkers}
            className={`toggle-button ${showRailMarkers ? 'rail-active' : ''}`}
          >
            {showRailMarkers ? 'Hide' : 'Show'} Rail
          </button>

          {/* Road layer toggle button */}
          <button
            id="toggleRoads"
            type="button"
            onClick={toggleRoadLayer}
            className={`toggle-button ${showRoadLayer ? 'road-active' : ''}`}
          >
            {showRoadLayer ? 'Hide' : 'Show'} Roads
          </button>

          {/* County animations toggle button */}
          <button
            id="toggleAnimations"
            type="button"
            onClick={toggleCountyAnimations}
            className={`toggle-button ${showCountyAnimations ? 'animation-active' : ''}`}
          >
            {showCountyAnimations ? 'Hide' : 'Show'} Animations
          </button>
        </div>
      </div>
    </>
  );
};

export default MapControls; 