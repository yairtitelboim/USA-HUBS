const fs = require('fs');
const path = require('path');

// Create data directory in public folder
const publicDataDir = path.join(__dirname, '../public/data');
if (!fs.existsSync(publicDataDir)) {
  fs.mkdirSync(publicDataDir, { recursive: true });
}

// Try to copy county_scores.geojson from LOGhub/data/final to public/data
try {
  const sourceFile = path.join(__dirname, '../../data/final/county_scores.geojson');
  const destFile = path.join(publicDataDir, 'county_scores.geojson');
  
  if (fs.existsSync(sourceFile)) {
    fs.copyFileSync(sourceFile, destFile);
    console.log('Successfully copied county_scores.geojson to public/data');
  } else {
    console.log('Source file not found, will use mock data instead');
  }
} catch (error) {
  console.error('Error copying county data:', error);
  console.log('Will use mock data instead');
}
