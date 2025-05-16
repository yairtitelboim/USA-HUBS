import numpy as np

# Create a range of obsolescence scores
obs_scores = np.linspace(0, 0.5, 100)  # Based on the observed range (max ~0.41)

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
current_growth_scores = [calculate_growth_score(score) for score in obs_scores]

print('Current formula analysis:')
print(f'Min obsolescence: {min(obs_scores):.3f}, Max obsolescence: {max(obs_scores):.3f}')
print(f'Min growth score: {min(current_growth_scores):.3f}, Max growth score: {max(current_growth_scores):.3f}')

# Test different calibrations
def calculate_growth_score_calibrated(obsolescence_score, offset=0.25, scale=1.0, invert=False, ndvi_value=0.4):
    # Estimate the raw indices based on typical values
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
    {'name': 'Lower offset', 'offset': 0.0, 'scale': 1.0, 'invert': False, 'ndvi': 0.4},
    {'name': 'Higher scale', 'offset': 0.25, 'scale': 2.0, 'invert': False, 'ndvi': 0.4},
    {'name': 'Inverted', 'offset': 0.25, 'scale': 1.0, 'invert': True, 'ndvi': 0.4},
    {'name': 'Higher NDVI', 'offset': 0.25, 'scale': 1.0, 'invert': False, 'ndvi': 0.6},
    {'name': 'Combined optimal', 'offset': -0.1, 'scale': 1.2, 'invert': False, 'ndvi': 0.5}
]

for cal in calibrations:
    growth_scores = [calculate_growth_score_calibrated(
        score, cal['offset'], cal['scale'], cal['invert'], cal['ndvi']
    ) for score in obs_scores]
    
    print(f'\n{cal["name"]} calibration:')
    print(f'Min growth score: {min(growth_scores):.3f}, Max growth score: {max(growth_scores):.3f}')
    
    # Check if we have values in the green range (below 0.2)
    green_values = [score for score in growth_scores if score < 0.2]
    if green_values:
        print(f'Has green values (< 0.2): Yes, {len(green_values)} values, min: {min(green_values):.3f}')
    else:
        print('Has green values (< 0.2): No')
