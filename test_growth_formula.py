import geopandas as gpd
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Load the data
data = gpd.read_file('data/final/county_scores.geojson')

# Current growth potential formula
def calculate_growth_score(obsolescence_score):
    # Estimate the raw indices based on typical values
    ndvi_value = 0.4  # Typical vegetation index value
    ndbi_value = (3 * obsolescence_score - 1 + ndvi_value) / 2  # Derived from obsolescence formula
    bsi_value = ndbi_value  # Assume similar to NDBI for simplicity
    
    # Ensure values are in reasonable ranges
    ndbi_value = max(-1, min(1, ndbi_value))
    bsi_value = max(-1, min(1, bsi_value))
    
    # Current formula for growth potential
    growth_score = max(0, min(1, 0.5 * (ndbi_value - 0.25) + 0.3 * (ndvi_value - 0.2) + 0.2 * bsi_value))
    return growth_score

# Calculate growth scores with current formula
data['current_growth_score'] = data['obsolescence_score'].apply(calculate_growth_score)

# Print statistics
print("Current growth score statistics:")
print(data['current_growth_score'].describe())
print("\nDistribution by ranges:")
print(data['current_growth_score'].value_counts(bins=10).sort_index())

# Test different calibrations
def calculate_growth_score_calibrated(obsolescence_score, offset=0.25, scale=1.0, invert=False):
    # Estimate the raw indices based on typical values
    ndvi_value = 0.4  # Typical vegetation index value
    ndbi_value = (3 * obsolescence_score - 1 + ndvi_value) / 2  # Derived from obsolescence formula
    bsi_value = ndbi_value  # Assume similar to NDBI for simplicity
    
    # Ensure values are in reasonable ranges
    ndbi_value = max(-1, min(1, ndbi_value))
    bsi_value = max(-1, min(1, bsi_value))
    
    # Calibrated formula with adjustable parameters
    base_score = 0.5 * (ndbi_value - offset) + 0.3 * (ndvi_value - 0.2) + 0.2 * bsi_value
    
    # Apply scaling
    scaled_score = base_score * scale
    
    # Optionally invert the relationship
    if invert:
        scaled_score = 1 - scaled_score
    
    # Clamp to 0-1 range
    growth_score = max(0, min(1, scaled_score))
    return growth_score

# Test a few calibrations
calibrations = [
    {"name": "Lower offset", "offset": 0.0, "scale": 1.0, "invert": False},
    {"name": "Higher scale", "offset": 0.25, "scale": 2.0, "invert": False},
    {"name": "Inverted", "offset": 0.25, "scale": 1.0, "invert": True},
    {"name": "Combined", "offset": 0.0, "scale": 1.5, "invert": False}
]

for cal in calibrations:
    col_name = f"growth_{cal['name'].lower().replace(' ', '_')}"
    data[col_name] = data['obsolescence_score'].apply(
        lambda x: calculate_growth_score_calibrated(
            x, cal['offset'], cal['scale'], cal['invert']
        )
    )
    print(f"\n{cal['name']} growth score statistics:")
    print(data[col_name].describe())
    print(f"\n{cal['name']} distribution by ranges:")
    print(data[col_name].value_counts(bins=10).sort_index())

# Plot the relationship between obsolescence and growth scores
plt.figure(figsize=(12, 8))

plt.subplot(2, 3, 1)
plt.scatter(data['obsolescence_score'], data['current_growth_score'], alpha=0.7)
plt.title('Current Formula')
plt.xlabel('Obsolescence Score')
plt.ylabel('Growth Score')
plt.grid(True, alpha=0.3)

for i, cal in enumerate(calibrations):
    col_name = f"growth_{cal['name'].lower().replace(' ', '_')}"
    plt.subplot(2, 3, i+2)
    plt.scatter(data['obsolescence_score'], data[col_name], alpha=0.7)
    plt.title(cal['name'])
    plt.xlabel('Obsolescence Score')
    plt.ylabel('Growth Score')
    plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('LOGhub/growth_formula_calibration.png')
print("\nPlot saved as 'growth_formula_calibration.png'")
