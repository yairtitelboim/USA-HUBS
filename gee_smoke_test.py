#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GEE Service Account Smoke Test

This script tests:
1. Authentication with GEE using service account
2. Pulling a small Sentinel-2 tile
3. Timing the round-trip for speed
4. Creating a quick visual via folium and thumbnail URL
"""

import os
import time
import datetime
import ee
import folium

# Set the path to the service account JSON file
service_account_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "config/gee/gentle-cinema-458613-f3-51d8ea2711e7.json"
)

# Export the path as an environment variable
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_path
print(f"Using service account: {service_account_path}")

# Initialize Earth Engine with service account credentials and project ID
try:
    # Set the environment variable for authentication
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_account_path

    # Initialize with project ID
    # This will use the credentials from the environment variable
    ee.Initialize(project="gentle-cinema-458613-f3")
    print("Earth Engine initialized successfully!")

    # Test with a simple API call
    test_image = ee.Image('USGS/SRTMGL1_003')
    test_info = test_image.getInfo()
    print("API test successful!")
except Exception as e:
    print(f"Error initializing Earth Engine: {e}")
    print("Detailed error information:", str(e))
    import traceback
    traceback.print_exc()
    exit(1)

# Define a small AOI (Area of Interest) - 1 km² box around Houston downtown
aoi = ee.Geometry.BBox(-95.37, 29.74, -95.36, 29.75)

# Define date range (last 18 months)
end = datetime.date.today()
start = end - datetime.timedelta(days=18*30)
print(f"Date range: {start} to {end}")

# Updated cloud-masking helper for Sentinel-2
def maskS2(img):
    # Use the cloud probability band (MSK_CLDPRB) and cloud classification bands
    # instead of the deprecated QA60 band
    cloudProb = img.select('MSK_CLDPRB')
    cloudOpaque = img.select('MSK_CLASSI_OPAQUE')
    cloudCirrus = img.select('MSK_CLASSI_CIRRUS')

    # Create a combined mask (cloud probability < 50% AND not classified as opaque or cirrus cloud)
    mask = cloudProb.lt(50).And(cloudOpaque.eq(0)).And(cloudCirrus.eq(0))

    # Apply the mask and scale the pixel values
    return img.updateMask(mask).divide(10000)

# Build & filter collection
print("Building and filtering Sentinel-2 collection...")
col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')  # Using the harmonized collection
         .filterBounds(aoi)
         .filterDate(str(start), str(end))
         .map(maskS2))

# Get collection size
size = col.size().getInfo()
print(f"Collection size: {size} images")

# Median composite
print("Creating median composite...")
median = col.median().select(['B4','B3','B2'])

# Time the API call
print("Timing API call for statistics...")
t0 = time.time()
info = median.reduceRegion(
    reducer=ee.Reducer.mean(),
    geometry=aoi,
    scale=10
).getInfo()
t1 = time.time()
print("Band means:", info)
print(f"Time to fetch stats: {t1-t0:.2f} s")

# Create a folium map
print("Creating folium map...")
vis = {'bands': ['B4','B3','B2'], 'min':0, 'max':0.3}
map_id = median.getMapId(vis)

m = folium.Map(location=[29.745, -95.365], zoom_start=13)
folium.TileLayer(
    tiles=map_id['tile_fetcher'].url_format,
    attr='Google Earth Engine',
).add_to(m)

# Save the map to an HTML file
map_file = "gee_map.html"
m.save(map_file)
print(f"Map saved to {map_file}")

# Get thumbnail URL
print("Generating thumbnail URL...")
thumb = median.getThumbURL({
    'region': aoi,
    'dimensions': [256, 256],
    'bands': ['B4','B3','B2'],
    'min': 0, 'max': 0.3
})
print("Thumbnail URL:", thumb)

print("\nSmoke test completed successfully!")
print("✅ Authentication works")
print(f"✅ Fetched stats in {t1-t0:.2f} s for small AOI")
print("✅ Generated map visualization and thumbnail URL")
