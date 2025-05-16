#!/usr/bin/env python3
"""
High Overlap Analysis Script

This script focuses specifically on counties that have both high obsolescence scores
and high growth potential scores, which seems counterintuitive. It provides detailed
analysis of these counties to understand if they represent data issues or interesting
patterns.
"""

import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Define paths
DATA_PATH = "../data/final/county_scores.geojson"
OUTPUT_PATH = "./overlap_analysis"

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

def find_overlap_counties(df, obs_threshold=0.5, growth_threshold=0.5):
    """
    Identify counties with both high obsolescence and high growth potential
    
    Args:
        df: DataFrame containing county data
        obs_threshold: Threshold for high obsolescence score (default: 0.5)
        growth_threshold: Threshold for high growth potential score (default: 0.5)
    
    Returns:
        DataFrame containing only counties that meet both thresholds
    """
    print(f"\nFinding counties with obsolescence > {obs_threshold} AND growth > {growth_threshold}...")
    
    # Filter counties that meet both criteria
    overlap_counties = df[(df['obsolescence_score'] > obs_threshold) & 
                         (df['growth_potential_score'] > growth_threshold)]
    
    print(f"Found {len(overlap_counties)} counties with both high obsolescence and high growth.")
    
    # Calculate what percentage of total counties this represents
    percentage = (len(overlap_counties) / len(df)) * 100
    print(f"This represents {percentage:.2f}% of all counties.")
    
    return overlap_counties

def analyze_overlap_distribution(df, overlap_df):
    """Analyze the distribution of scores in the overlap counties vs all counties"""
    print("\nAnalyzing score distributions...")
    
    # Calculate basic statistics
    stats_all = df[['obsolescence_score', 'growth_potential_score']].describe()
    stats_overlap = overlap_df[['obsolescence_score', 'growth_potential_score']].describe()
    
    print("\nAll Counties Statistics:")
    print(stats_all)
    
    print("\nOverlap Counties Statistics:")
    print(stats_overlap)
    
    # Create distribution comparison plot
    plt.figure(figsize=(12, 8))
    
    # Obsolescence score distribution comparison
    plt.subplot(2, 1, 1)
    sns.kdeplot(df['obsolescence_score'], label='All Counties', color='blue')
    sns.kdeplot(overlap_df['obsolescence_score'], label='Overlap Counties', color='red')
    plt.xlabel('Obsolescence Score')
    plt.ylabel('Density')
    plt.title('Distribution of Obsolescence Scores')
    plt.legend()
    
    # Growth potential score distribution comparison
    plt.subplot(2, 1, 2)
    sns.kdeplot(df['growth_potential_score'], label='All Counties', color='blue')
    sns.kdeplot(overlap_df['growth_potential_score'], label='Overlap Counties', color='red')
    plt.xlabel('Growth Potential Score')
    plt.ylabel('Density')
    plt.title('Distribution of Growth Potential Scores')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_PATH, 'overlap_distributions.png'), dpi=300)
    print(f"Saved distribution comparison to {os.path.join(OUTPUT_PATH, 'overlap_distributions.png')}")

def create_scatterplot(df, overlap_df):
    """Create a scatter plot highlighting the overlap counties"""
    print("\nCreating scatter plot with highlighted overlap counties...")
    
    plt.figure(figsize=(10, 8))
    
    # Plot all counties in light gray
    plt.scatter(df['obsolescence_score'], df['growth_potential_score'], 
               color='lightgray', alpha=0.6, label='Other Counties')
    
    # Plot overlap counties in red
    plt.scatter(overlap_df['obsolescence_score'], overlap_df['growth_potential_score'], 
               color='red', alpha=0.8, label='High Overlap Counties')
    
    # Add quadrant lines
    plt.axhline(y=0.5, color='black', linestyle='--', alpha=0.3)
    plt.axvline(x=0.5, color='black', linestyle='--', alpha=0.3)
    
    plt.xlabel('Obsolescence Score')
    plt.ylabel('Growth Potential Score')
    plt.title('Counties with High Obsolescence and High Growth Potential')
    plt.legend()
    plt.grid(alpha=0.3)
    
    # Add text labels for extreme overlap counties (top 5)
    extreme_counties = overlap_df.sort_values(by=['obsolescence_score', 'growth_potential_score'], 
                                             ascending=False).head(5)
    
    for _, county in extreme_counties.iterrows():
        plt.annotate(county['NAME'], 
                    xy=(county['obsolescence_score'], county['growth_potential_score']),
                    xytext=(5, 5), textcoords='offset points',
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))
    
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_PATH, 'overlap_scatter.png'), dpi=300)
    print(f"Saved scatter plot to {os.path.join(OUTPUT_PATH, 'overlap_scatter.png')}")

def generate_report(overlap_df):
    """Generate a detailed report of the overlap counties"""
    print("\nGenerating detailed report of overlap counties...")
    
    # Sort by combined score (sum of both metrics)
    sorted_overlap = overlap_df.sort_values(
        by=['obsolescence_score', 'growth_potential_score'], 
        ascending=False
    )
    
    # Add a combined score column
    sorted_overlap['combined_score'] = sorted_overlap['obsolescence_score'] + sorted_overlap['growth_potential_score']
    
    # Export the full report to CSV
    report_cols = ['GEOID', 'NAME', 'STATEFP', 'obsolescence_score', 
                  'growth_potential_score', 'combined_score']
    
    if all(col in sorted_overlap.columns for col in report_cols):
        report_df = sorted_overlap[report_cols]
        report_df.to_csv(os.path.join(OUTPUT_PATH, 'high_overlap_counties.csv'), index=False)
        print(f"Exported full report to {os.path.join(OUTPUT_PATH, 'high_overlap_counties.csv')}")
    else:
        missing_cols = [col for col in report_cols if col not in sorted_overlap.columns]
        print(f"Warning: Could not export full report due to missing columns: {missing_cols}")
        # Export with available columns
        available_cols = [col for col in report_cols if col in sorted_overlap.columns]
        sorted_overlap[available_cols].to_csv(os.path.join(OUTPUT_PATH, 'high_overlap_counties.csv'), index=False)
        print(f"Exported report with available columns to {os.path.join(OUTPUT_PATH, 'high_overlap_counties.csv')}")
    
    # Create a text report of the top 20 most extreme cases
    top_counties = sorted_overlap.head(20)
    
    with open(os.path.join(OUTPUT_PATH, 'top_overlap_counties.txt'), 'w') as f:
        f.write("TOP COUNTIES WITH HIGH OBSOLESCENCE AND HIGH GROWTH POTENTIAL\n")
        f.write("=============================================================\n\n")
        
        for i, (_, county) in enumerate(top_counties.iterrows()):
            f.write(f"{i+1}. {county.get('NAME', 'Unknown')}\n")
            f.write(f"   State: {county.get('STATEFP', 'Unknown')}\n")
            f.write(f"   Obsolescence Score: {county.get('obsolescence_score', 0):.4f}\n")
            f.write(f"   Growth Potential: {county.get('growth_potential_score', 0):.4f}\n")
            f.write(f"   Combined Score: {county.get('combined_score', 0):.4f}\n\n")
    
    print(f"Created text report of top 20 counties at {os.path.join(OUTPUT_PATH, 'top_overlap_counties.txt')}")

def analyze_by_thresholds(df):
    """Analyze overlap distribution across different thresholds"""
    print("\nAnalyzing overlap across different threshold combinations...")
    
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    results = []
    
    for obs_threshold in thresholds:
        for growth_threshold in thresholds:
            overlap_count = len(df[(df['obsolescence_score'] > obs_threshold) & 
                                  (df['growth_potential_score'] > growth_threshold)])
            percentage = (overlap_count / len(df)) * 100
            
            results.append({
                'Obsolescence Threshold': obs_threshold,
                'Growth Threshold': growth_threshold,
                'Count': overlap_count,
                'Percentage': percentage
            })
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    
    # Create a heatmap of the results
    plt.figure(figsize=(10, 8))
    
    # Pivot the data for the heatmap
    heatmap_data = results_df.pivot(
        index='Obsolescence Threshold', 
        columns='Growth Threshold', 
        values='Percentage'
    )
    
    # Plot the heatmap
    sns.heatmap(heatmap_data, annot=True, fmt=".1f", cmap="YlOrRd")
    plt.title('Percentage of Counties Above Both Thresholds')
    plt.xlabel('Growth Potential Threshold')
    plt.ylabel('Obsolescence Threshold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_PATH, 'threshold_analysis.png'), dpi=300)
    print(f"Saved threshold analysis to {os.path.join(OUTPUT_PATH, 'threshold_analysis.png')}")
    
    # Export the results
    results_df.to_csv(os.path.join(OUTPUT_PATH, 'threshold_analysis.csv'), index=False)

def main():
    """Main function to run the analysis"""
    # Load data
    df = load_county_data()
    if df is None:
        return
    
    # Ensure the required columns exist and are numeric
    required_cols = ['obsolescence_score', 'growth_potential_score']
    if not all(col in df.columns for col in required_cols):
        print(f"Error: Dataset is missing required columns: {[col for col in required_cols if col not in df.columns]}")
        return
    
    # Convert to numeric if needed
    for col in required_cols:
        if df[col].dtype not in ['float64', 'int64']:
            print(f"Converting {col} to numeric...")
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Find counties with both high obsolescence and high growth
    overlap_df = find_overlap_counties(df)
    
    if len(overlap_df) == 0:
        print("No counties found meeting the criteria. Try lowering the thresholds.")
        return
    
    # Analyze distributions
    analyze_overlap_distribution(df, overlap_df)
    
    # Create visualization
    create_scatterplot(df, overlap_df)
    
    # Generate detailed report
    generate_report(overlap_df)
    
    # Analyze across different thresholds
    analyze_by_thresholds(df)
    
    print("\nHigh overlap analysis complete!")

if __name__ == "__main__":
    main() 