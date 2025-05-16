import React from 'react';
import './Legend.css';

/**
 * Legend Component for the map
 * Displays the appropriate legend based on the current metric
 * 
 * @param {string} props.currentMetric - The current metric being displayed ('obsolescence_score' or 'growth_potential_score')
 * @param {boolean} props.isCombinedView - Whether the map is showing the combined view
 */
const Legend = ({ 
  currentMetric, 
  isCombinedView
}) => {
  // Determine which metric is being displayed
  const isObsolescence = currentMetric === 'obsolescence_score';
  
  // Set the title and colors based on the current metric
  const title = isObsolescence ? 'Obsolescence Score' : 'Growth Potential';
  
  // Only show the standard legend when we're not in combined view
  if (!isCombinedView) {
    return (
      <div id="legend">
        <h3>{title}</h3>
        <div className="gradient-bar">
          <div className={`gradient ${isObsolescence ? 'obsolescence-gradient' : 'growth-gradient'}`}></div>
          <div className="labels">
            <span>Low</span>
            <span>High</span>
          </div>
        </div>
        <div className="legend-footer">
          <p className="legend-description">
            {isObsolescence ? 
              'Higher scores indicate greater obsolescence risk.' : 
              'Higher scores indicate greater growth potential.'}
          </p>
        </div>
      </div>
    );
  }
  
  // Combined view legend
  return (
    <div id="legend" className="combined-legend">
      <h3>Combined Analysis</h3>
      <div className="combined-legend-container">
        <div className="combined-metrics">
          <div className="combined-metric-item">
            <span className="metric-label">Horizontal:</span>
            <span className="metric-name">Growth Potential</span>
            <div className="metric-gradient growth-gradient"></div>
            <div className="metric-labels">
              <span>Low</span>
              <span>High</span>
            </div>
          </div>
          <div className="combined-metric-item">
            <span className="metric-label">Vertical:</span>
            <span className="metric-name">Obsolescence</span>
            <div className="metric-gradient obsolescence-gradient"></div>
            <div className="metric-labels">
              <span>Low</span>
              <span>High</span>
            </div>
          </div>
        </div>
        <div className="combined-matrix">
          <div className="matrix-square top-right">
            <span className="matrix-label">High Obsolescence<br/>High Growth</span>
          </div>
          <div className="matrix-square top-left">
            <span className="matrix-label">High Obsolescence<br/>Low Growth</span>
          </div>
          <div className="matrix-square bottom-right">
            <span className="matrix-label">Low Obsolescence<br/>High Growth</span>
          </div>
          <div className="matrix-square bottom-left">
            <span className="matrix-label">Low Obsolescence<br/>Low Growth</span>
          </div>
        </div>
      </div>
      <div className="combined-footer">
        <p>This view combines obsolescence risk and growth potential metrics.</p>
      </div>
    </div>
  );
};

export default Legend; 