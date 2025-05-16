#!/usr/bin/env python3
import json
import numpy as np
from collections import Counter

# Load the data
with open('data/final/county_scores.geojson') as f:
    data = json.load(f)

features = data['features']
print(f'Total counties: {len(features)}')

# Extract scores
counties_with_both = []
obs_scores = []
growth_scores = []
high_obs_high_growth = []
high_obs_low_growth = []
low_obs_high_growth = []
low_obs_low_growth = []

for feature in features:
    props = feature['properties']
    if 'obsolescence_score' in props and 'growth_potential_score' in props:
        obs = props['obsolescence_score']
        growth = props['growth_potential_score']
        
        counties_with_both.append(props)
        obs_scores.append(obs)
        growth_scores.append(growth)
        
        # Categorize counties
        if obs > 0.7 and growth > 0.7:
            high_obs_high_growth.append(props)
        elif obs > 0.7 and growth < 0.3:
            high_obs_low_growth.append(props)
        elif obs < 0.3 and growth > 0.7:
            low_obs_high_growth.append(props)
        elif obs < 0.3 and growth < 0.3:
            low_obs_low_growth.append(props)

print(f'Counties with both scores: {len(counties_with_both)}')

# Calculate correlation
correlation = np.corrcoef(obs_scores, growth_scores)[0, 1]
print(f'\nCorrelation between obsolescence and growth: {correlation:.4f}')

# Print distribution
print('\nDistribution:')
print(f'High obsolescence (>0.7), High growth (>0.7): {len(high_obs_high_growth)}')
print(f'High obsolescence (>0.7), Low growth (<0.3): {len(high_obs_low_growth)}')
print(f'Low obsolescence (<0.3), High growth (>0.7): {len(low_obs_high_growth)}')
print(f'Low obsolescence (<0.3), Low growth (<0.3): {len(low_obs_low_growth)}')

# Print examples of high-high counties
print('\nSample high obsolescence, high growth counties:')
for county in high_obs_high_growth[:5]:
    print(f"County: {county['NAME']}, {county['NAMELSAD']}, Obsolescence: {county['obsolescence_score']:.4f}, Growth: {county['growth_potential_score']:.4f}")

# Print examples of low-high counties
print('\nSample low obsolescence, high growth counties:')
for county in low_obs_high_growth[:5]:
    print(f"County: {county['NAME']}, {county['NAMELSAD']}, Obsolescence: {county['obsolescence_score']:.4f}, Growth: {county['growth_potential_score']:.4f}")

# Print examples of high-low counties
print('\nSample high obsolescence, low growth counties:')
for county in high_obs_low_growth[:5]:
    print(f"County: {county['NAME']}, {county['NAMELSAD']}, Obsolescence: {county['obsolescence_score']:.4f}, Growth: {county['growth_potential_score']:.4f}")

# Analyze the distribution of scores
obs_bins = np.linspace(0, 1, 6)  # 0.0, 0.2, 0.4, 0.6, 0.8, 1.0
growth_bins = np.linspace(0, 1, 6)

obs_hist, _ = np.histogram(obs_scores, bins=obs_bins)
growth_hist, _ = np.histogram(growth_scores, bins=growth_bins)

print('\nObsolescence score distribution:')
for i in range(len(obs_bins)-1):
    print(f'{obs_bins[i]:.1f}-{obs_bins[i+1]:.1f}: {obs_hist[i]} counties ({obs_hist[i]/len(obs_scores)*100:.1f}%)')

print('\nGrowth potential score distribution:')
for i in range(len(growth_bins)-1):
    print(f'{growth_bins[i]:.1f}-{growth_bins[i+1]:.1f}: {growth_hist[i]} counties ({growth_hist[i]/len(growth_scores)*100:.1f}%)')

# Create a 2D histogram to see the joint distribution
hist_2d, _, _ = np.histogram2d(obs_scores, growth_scores, bins=[obs_bins, growth_bins])

print('\n2D distribution (rows=obsolescence, columns=growth):')
for i in range(len(obs_bins)-1):
    row = []
    for j in range(len(growth_bins)-1):
        count = hist_2d[i, j]
        percentage = count / len(obs_scores) * 100
        row.append(f'{count:.0f} ({percentage:.1f}%)')
    print(f'Obs {obs_bins[i]:.1f}-{obs_bins[i+1]:.1f}: {row}')
