import json
import shapefile
import os

# Check the county scores data
print("Checking county scores data...")
with open('data/final/county_scores.geojson', 'r') as f:
    county_scores = json.load(f)

# Print the first feature's properties to see the structure
if county_scores['features']:
    print("\nFirst county score feature properties:")
    props = county_scores['features'][0]['properties']
    for key, value in props.items():
        print(f"  {key}: {value}")

# Check for county_fips field
fips_fields = set()
for feature in county_scores['features']:
    for key in feature['properties'].keys():
        if 'fips' in key.lower() or 'geoid' in key.lower():
            fips_fields.add(key)

print(f"\nPossible FIPS fields in county scores: {fips_fields}")

# Check the shapefile data
print("\nChecking shapefile data...")
sf = shapefile.Reader('data/tl_2024_us_county/tl_2024_us_county.shp')

# Print the field names
print("\nShapefile fields:")
for field in sf.fields[1:]:  # Skip the deletion flag field
    print(f"  {field[0]}")

# Print the first record's attributes
if sf.records():
    print("\nFirst shapefile record:")
    record = sf.record(0)
    for i, field in enumerate(sf.fields[1:]):
        print(f"  {field[0]}: {record[i]}")

# Check for GEOID field
geoid_fields = set()
for i, field in enumerate(sf.fields[1:]):
    if 'fips' in field[0].lower() or 'geoid' in field[0].lower():
        geoid_fields.add(field[0])

print(f"\nPossible FIPS/GEOID fields in shapefile: {geoid_fields}")

# Check for matching FIPS codes
print("\nChecking for matching FIPS codes...")
county_fips = set()
for feature in county_scores['features']:
    if 'county_fips' in feature['properties']:
        county_fips.add(feature['properties']['county_fips'])

shapefile_geoids = set()
for i in range(len(sf.records())):
    record = sf.record(i)
    for j, field in enumerate(sf.fields[1:]):
        if field[0] == 'GEOID':
            shapefile_geoids.add(record[j])

print(f"County scores has {len(county_fips)} unique FIPS codes")
print(f"Shapefile has {len(shapefile_geoids)} unique GEOID values")

# Check for overlap
overlap = county_fips.intersection(shapefile_geoids)
print(f"Overlap: {len(overlap)} matching FIPS codes")

# Print some examples from both sets
print("\nSample county_fips from county_scores:")
for fips in list(county_fips)[:5]:
    print(f"  {fips}")

print("\nSample GEOID from shapefile:")
for geoid in list(shapefile_geoids)[:5]:
    print(f"  {geoid}")
