#!/usr/bin/env python3
"""
County Data Validation Script

This script analyzes the relationship between obsolescence_score and growth_potential_score
in the county visualization data. It performs data validation, statistical analysis,
and visualization to understand the correlation between these two metrics.
"""

import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from scipy import stats

# Define paths
DATA_PATH = "../data/final/county_scores.geojson"
OUTPUT_PATH = "./analysis_results"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_PATH, exist_ok=True)

def load_county_data():
    """Load county GeoJSON data and convert to DataFrame"""
    print(f"Loading data from {DATA_PATH}...")
    
    try:
        with open(DATA_PATH, 'r') as file:
            county_data = json.load(file)
    except FileNotFoundError:
        print(f"Error: File {DATA_PATH} not found. Please check the path.")
        return None
    except json.JSONDecodeError:
        print(f"Error: File {DATA_PATH} contains invalid JSON.")
        return None
    
    # Extract properties from features
    features = county_data.get('features', [])
    if not features:
        print("Error: No features found in the GeoJSON file.")
        return None
    
    properties_list = []
    for feature in features:
        props = feature.get('properties', {})
        if props:
            properties_list.append(props)
    
    df = pd.DataFrame(properties_list)
    print(f"Loaded {len(df)} counties.")
    return df

def validate_data(df):
    """Validate the data structure and check for issues"""
    print("\n==== Data Validation ====")
    
    # Check for required columns
    required_cols = ['NAME', 'GEOID', 'obsolescence_score', 'growth_potential_score']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"Error: Missing required columns: {missing_cols}")
        return False
    
    # Check for missing values
    null_counts = df[required_cols].isnull().sum()
    if null_counts.sum() > 0:
        print(f"Warning: Found missing values:\n{null_counts}")
    
    # Check data types and range
    numeric_cols = ['obsolescence_score', 'growth_potential_score']
    for col in numeric_cols:
        if df[col].dtype not in ['float64', 'int64']:
            print(f"Warning: Column {col} is not numeric, converting...")
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        min_val = df[col].min()
        max_val = df[col].max()
        print(f"{col}: Range [{min_val:.4f}, {max_val:.4f}]")
        
        if min_val < 0 or max_val > 1:
            print(f"Warning: {col} has values outside the expected [0,1] range.")
    
    # Check for duplicates
    if df['GEOID'].duplicated().any():
        print(f"Warning: Found {df['GEOID'].duplicated().sum()} duplicate GEOID values.")
    
    return True

def analyze_correlation(df):
    """Analyze the correlation between obsolescence and growth scores"""
    print("\n==== Correlation Analysis ====")
    
    # Calculate correlation coefficients
    pearson_corr = df['obsolescence_score'].corr(df['growth_potential_score'])
    spearman_corr = df['obsolescence_score'].corr(df['growth_potential_score'], method='spearman')
    
    print(f"Pearson correlation: {pearson_corr:.4f}")
    print(f"Spearman rank correlation: {spearman_corr:.4f}")
    
    # Interpret correlation
    if abs(pearson_corr) < 0.3:
        strength = "weak"
    elif abs(pearson_corr) < 0.7:
        strength = "moderate"
    else:
        strength = "strong"
    
    direction = "positive" if pearson_corr > 0 else "negative"
    print(f"The correlation is {strength} and {direction}.")
    
    # Statistical significance test
    t_stat, p_value = stats.pearsonr(df['obsolescence_score'], df['growth_potential_score'])
    print(f"p-value: {p_value:.6f}")
    
    if p_value < 0.05:
        print("The correlation is statistically significant (p < 0.05).")
    else:
        print("The correlation is not statistically significant (p >= 0.05).")
    
    return pearson_corr, spearman_corr, p_value

def identify_outliers(df):
    """Identify counties that have unusual combinations of scores"""
    print("\n==== Identifying Notable Counties ====")
    
    # Calculate z-scores for both metrics
    df['obs_zscore'] = stats.zscore(df['obsolescence_score'])
    df['growth_zscore'] = stats.zscore(df['growth_potential_score'])
    
    # Define categories of interest
    high_both = df[(df['obsolescence_score'] > 0.7) & (df['growth_potential_score'] > 0.7)]
    low_both = df[(df['obsolescence_score'] < 0.3) & (df['growth_potential_score'] < 0.3)]
    high_obs_low_growth = df[(df['obsolescence_score'] > 0.7) & (df['growth_potential_score'] < 0.3)]
    low_obs_high_growth = df[(df['obsolescence_score'] < 0.3) & (df['growth_potential_score'] > 0.7)]
    
    # Print notable counties in each category
    categories = {
        "High Obsolescence & High Growth": high_both,
        "Low Obsolescence & Low Growth": low_both,
        "High Obsolescence & Low Growth": high_obs_low_growth,
        "Low Obsolescence & High Growth": low_obs_high_growth
    }
    
    for category, subset in categories.items():
        print(f"\n{category}: {len(subset)} counties")
        if len(subset) > 0:
            # Sort by combined score (sum of both metrics)
            sorted_subset = subset.sort_values(by=['obsolescence_score', 'growth_potential_score'], 
                                              ascending=False)
            # Show top 5 counties in each category
            top_counties = sorted_subset.head(5)[['NAME', 'obsolescence_score', 'growth_potential_score']]
            for _, row in top_counties.iterrows():
                print(f"  {row['NAME']}: Obs={row['obsolescence_score']:.4f}, Growth={row['growth_potential_score']:.4f}")
    
    # Return the most interesting counties for detailed analysis
    return high_both

def create_visualizations(df):
    """Create visualizations of the data"""
    print("\n==== Creating Visualizations ====")
    
    # Set the aesthetic style of the plots
    sns.set_style('darkgrid')
    plt.figure(figsize=(10, 8))
    
    # Custom colormap to match the visualization in the app
    cmap = LinearSegmentedColormap.from_list(
        'custom_cmap', 
        ['#0a1446', '#1e3c64', '#3264a0', '#46a0c8', '#64c8c8', '#7dd29b', '#a0dc82', '#d2e164', '#fad24b', '#fa9632', '#f06e14', '#dc0000']
    )
    
    # 1. Scatter plot of obsolescence vs growth
    plt.subplot(2, 2, 1)
    scatter = plt.scatter(df['obsolescence_score'], df['growth_potential_score'], 
                         c=df['obsolescence_score'], cmap=cmap, alpha=0.7)
    plt.colorbar(scatter, label='Obsolescence Score')
    plt.xlabel('Obsolescence Score')
    plt.ylabel('Growth Potential Score')
    plt.title('Relationship between Obsolescence and Growth')
    
    # Draw trendline
    z = np.polyfit(df['obsolescence_score'], df['growth_potential_score'], 1)
    p = np.poly1d(z)
    plt.plot(np.linspace(0, 1, 100), p(np.linspace(0, 1, 100)), "r--", alpha=0.8)
    
    # 2. Joint distribution plot
    plt.subplot(2, 2, 2)
    H, xedges, yedges = np.histogram2d(
        df['obsolescence_score'], df['growth_potential_score'], 
        bins=20, range=[[0, 1], [0, 1]]
    )
    plt.imshow(H.T, origin='lower', extent=[0, 1, 0, 1], 
              aspect='auto', cmap='viridis')
    plt.colorbar(label='Count')
    plt.xlabel('Obsolescence Score')
    plt.ylabel('Growth Potential Score')
    plt.title('2D Histogram of Scores')
    
    # 3. Distribution of obsolescence scores
    plt.subplot(2, 2, 3)
    sns.histplot(df['obsolescence_score'], kde=True, bins=30, color='blue')
    plt.xlabel('Obsolescence Score')
    plt.title('Distribution of Obsolescence Scores')
    
    # 4. Distribution of growth potential scores
    plt.subplot(2, 2, 4)
    sns.histplot(df['growth_potential_score'], kde=True, bins=30, color='green')
    plt.xlabel('Growth Potential Score')
    plt.title('Distribution of Growth Potential Scores')
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_PATH, 'county_scores_analysis.png'), dpi=300)
    print(f"Saved visualization to {os.path.join(OUTPUT_PATH, 'county_scores_analysis.png')}")
    
    # Create a quadrant analysis
    plt.figure(figsize=(12, 10))
    
    # Create 4 quadrants
    plt.axhline(y=0.5, color='gray', linestyle='--', alpha=0.7)
    plt.axvline(x=0.5, color='gray', linestyle='--', alpha=0.7)
    
    # Add text for quadrants
    plt.text(0.25, 0.75, "Low Obsolescence\nHigh Growth", 
             horizontalalignment='center', verticalalignment='center',
             bbox=dict(facecolor='white', alpha=0.5))
    
    plt.text(0.75, 0.75, "High Obsolescence\nHigh Growth", 
             horizontalalignment='center', verticalalignment='center',
             bbox=dict(facecolor='white', alpha=0.5))
    
    plt.text(0.25, 0.25, "Low Obsolescence\nLow Growth", 
             horizontalalignment='center', verticalalignment='center',
             bbox=dict(facecolor='white', alpha=0.5))
    
    plt.text(0.75, 0.25, "High Obsolescence\nLow Growth", 
             horizontalalignment='center', verticalalignment='center',
             bbox=dict(facecolor='white', alpha=0.5))
    
    # Scatter plot with color intensity based on score sum
    df['score_sum'] = df['obsolescence_score'] + df['growth_potential_score']
    scatter = plt.scatter(df['obsolescence_score'], df['growth_potential_score'], 
                         c=df['score_sum'], cmap='viridis', 
                         alpha=0.7, s=30)
    
    plt.colorbar(scatter, label='Sum of Scores')
    plt.xlabel('Obsolescence Score')
    plt.ylabel('Growth Potential Score')
    plt.title('Quadrant Analysis of Obsolescence vs Growth')
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_PATH, 'quadrant_analysis.png'), dpi=300)
    print(f"Saved quadrant analysis to {os.path.join(OUTPUT_PATH, 'quadrant_analysis.png')}")

def export_results(df, interesting_counties):
    """Export analysis results to CSV files"""
    
    # Export full dataset with analysis columns
    df_export = df[['GEOID', 'NAME', 'obsolescence_score', 'growth_potential_score', 
                   'obs_zscore', 'growth_zscore']]
    df_export.to_csv(os.path.join(OUTPUT_PATH, 'county_analysis.csv'), index=False)
    
    # Export interesting counties
    if len(interesting_counties) > 0:
        interesting_counties.to_csv(os.path.join(OUTPUT_PATH, 'interesting_counties.csv'), index=False)
    
    print(f"\nExported analysis results to {OUTPUT_PATH}")

def main():
    """Main function to run the analysis"""
    # Load data
    df = load_county_data()
    if df is None:
        return
    
    # Validate data
    if not validate_data(df):
        return
    
    # Analyze correlation
    analyze_correlation(df)
    
    # Identify outliers and interesting counties
    interesting_counties = identify_outliers(df)
    
    # Create visualizations
    create_visualizations(df)
    
    # Export results
    export_results(df, interesting_counties)
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main() 