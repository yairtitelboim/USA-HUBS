#!/usr/bin/env python3
"""
Generate County Report

This script generates a comprehensive HTML report about the county data,
including statistics, visualizations, and top/bottom counties by obsolescence score.

Usage:
    python generate_county_report.py [--input INPUT_FILE] [--output OUTPUT_FILE]

Options:
    --input INPUT_FILE    Path to the county scores GeoJSON [default: data/final/comprehensive_county_scores.geojson]
    --output OUTPUT_FILE  Path to save the HTML report [default: qa/county_data_report.html]
"""

import os
import json
import argparse
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import base64
from io import BytesIO
from datetime import datetime

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate county report')
    parser.add_argument('--input', default='data/final/comprehensive_county_scores.geojson',
                        help='Path to the county scores GeoJSON')
    parser.add_argument('--output', default='qa/county_data_report.html',
                        help='Path to save the HTML report')
    return parser.parse_args()

def fig_to_base64(fig):
    """Convert matplotlib figure to base64 string for HTML embedding."""
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    return img_str

def generate_score_distribution_plot(gdf):
    """Generate a plot of the obsolescence score distribution."""
    fig, ax = plt.subplots(figsize=(10, 6))
    gdf['obsolescence_score'].hist(bins=20, ax=ax, color='skyblue', edgecolor='black')
    ax.set_title('Distribution of Obsolescence Scores', fontsize=14)
    ax.set_xlabel('Obsolescence Score', fontsize=12)
    ax.set_ylabel('Number of Counties', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.7)
    return fig

def generate_regional_comparison_plot(gdf):
    """Generate a plot comparing obsolescence scores by region."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Create a box plot by region
    regions = ['Northeast', 'Midwest', 'South', 'West']
    data = [gdf[gdf['REGION'] == region]['obsolescence_score'] for region in regions]
    
    box = ax.boxplot(data, patch_artist=True, labels=regions)
    
    # Set colors for each box
    colors = ['lightblue', 'lightgreen', 'salmon', 'khaki']
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
    
    ax.set_title('Obsolescence Scores by Region', fontsize=14)
    ax.set_xlabel('Region', fontsize=12)
    ax.set_ylabel('Obsolescence Score', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.5, axis='y')
    
    return fig

def generate_state_heatmap(gdf):
    """Generate a heatmap of average obsolescence scores by state."""
    # Calculate average score by state
    state_scores = gdf.groupby('STATEFP')['obsolescence_score'].mean().reset_index()
    state_scores = state_scores.sort_values('obsolescence_score', ascending=False)
    
    # Get state names if available
    if 'STATE' in gdf.columns:
        state_names = gdf[['STATEFP', 'STATE']].drop_duplicates()
        state_scores = state_scores.merge(state_names, on='STATEFP', how='left')
        state_labels = state_scores['STATE'].values
    else:
        state_labels = state_scores['STATEFP'].values
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Limit to top 20 states if there are many
    if len(state_scores) > 20:
        state_scores = state_scores.head(20)
        state_labels = state_labels[:20]
    
    im = ax.imshow([state_scores['obsolescence_score'].values], cmap='RdYlBu_r', aspect='auto')
    
    # Add colorbar
    cbar = fig.colorbar(im, ax=ax, orientation='horizontal', pad=0.2)
    cbar.set_label('Average Obsolescence Score')
    
    # Add state labels
    ax.set_yticks([])
    ax.set_xticks(np.arange(len(state_labels)))
    ax.set_xticklabels(state_labels, rotation=45, ha='right')
    
    ax.set_title('Top States by Average Obsolescence Score', fontsize=14)
    
    return fig

def generate_county_report(input_file, output_file):
    """Generate a comprehensive HTML report about the county data."""
    print(f"Loading county data from {input_file}...")
    
    # Load the GeoJSON file
    try:
        gdf = gpd.read_file(input_file)
        print(f"Loaded {len(gdf)} counties from GeoJSON file")
    except Exception as e:
        print(f"Error loading GeoJSON file: {e}")
        return
    
    # Basic statistics
    total_counties = len(gdf)
    counties_with_data = len(gdf[gdf['obsolescence_score'] > 0])
    coverage_percentage = (counties_with_data / total_counties) * 100
    
    score_stats = {
        "min": float(gdf['obsolescence_score'].min()),
        "max": float(gdf['obsolescence_score'].max()),
        "mean": float(gdf['obsolescence_score'].mean()),
        "median": float(gdf['obsolescence_score'].median()),
        "std": float(gdf['obsolescence_score'].std())
    }
    
    # Get top and bottom counties by score
    top_counties = gdf.sort_values('obsolescence_score', ascending=False).head(10)
    bottom_counties = gdf.sort_values('obsolescence_score').head(10)
    
    # Generate visualizations
    print("Generating visualizations...")
    score_dist_fig = generate_score_distribution_plot(gdf)
    score_dist_img = fig_to_base64(score_dist_fig)
    plt.close(score_dist_fig)
    
    # Regional comparison if region data is available
    if 'REGION' in gdf.columns:
        regional_fig = generate_regional_comparison_plot(gdf)
        regional_img = fig_to_base64(regional_fig)
        plt.close(regional_fig)
    else:
        regional_img = None
    
    # State heatmap
    state_heatmap_fig = generate_state_heatmap(gdf)
    state_heatmap_img = fig_to_base64(state_heatmap_fig)
    plt.close(state_heatmap_fig)
    
    # Generate HTML report
    print("Generating HTML report...")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>County Data Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            h1, h2, h3 {{
                color: #2c3e50;
            }}
            .container {{
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            .stat-box {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .stat-value {{
                font-size: 24px;
                font-weight: bold;
                color: #3498db;
            }}
            .stat-label {{
                font-size: 14px;
                color: #7f8c8d;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .visualization {{
                margin: 30px 0;
                text-align: center;
            }}
            .visualization img {{
                max-width: 100%;
                height: auto;
                border-radius: 5px;
                box-shadow: 0 3px 10px rgba(0,0,0,0.2);
            }}
            footer {{
                margin-top: 30px;
                text-align: center;
                font-size: 14px;
                color: #7f8c8d;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>County Obsolescence Score Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Data source: {input_file}</p>
        </div>
        
        <div class="container">
            <h2>Data Coverage</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-value">{total_counties}</div>
                    <div class="stat-label">Total Counties</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{counties_with_data}</div>
                    <div class="stat-label">Counties with Data</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{coverage_percentage:.2f}%</div>
                    <div class="stat-label">Coverage</div>
                </div>
            </div>
        </div>
        
        <div class="container">
            <h2>Score Statistics</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-value">{score_stats['min']:.2f}</div>
                    <div class="stat-label">Minimum Score</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{score_stats['max']:.2f}</div>
                    <div class="stat-label">Maximum Score</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{score_stats['mean']:.2f}</div>
                    <div class="stat-label">Mean Score</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{score_stats['median']:.2f}</div>
                    <div class="stat-label">Median Score</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{score_stats['std']:.2f}</div>
                    <div class="stat-label">Standard Deviation</div>
                </div>
            </div>
            
            <div class="visualization">
                <h3>Score Distribution</h3>
                <img src="data:image/png;base64,{score_dist_img}" alt="Score Distribution">
            </div>
    """
    
    # Add regional comparison if available
    if regional_img:
        html_content += f"""
            <div class="visualization">
                <h3>Regional Comparison</h3>
                <img src="data:image/png;base64,{regional_img}" alt="Regional Comparison">
            </div>
        """
    
    # Add state heatmap
    html_content += f"""
            <div class="visualization">
                <h3>Top States by Average Obsolescence Score</h3>
                <img src="data:image/png;base64,{state_heatmap_img}" alt="State Heatmap">
            </div>
        </div>
        
        <div class="container">
            <h2>Top 10 Counties by Obsolescence Score</h2>
            <table>
                <thead>
                    <tr>
                        <th>County</th>
                        <th>State</th>
                        <th>Obsolescence Score</th>
                        <th>Confidence</th>
                        <th>Tile Count</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Add top counties
    for _, row in top_counties.iterrows():
        county_name = row.get('NAME', 'Unknown')
        state_name = row.get('STATE', row.get('STATEFP', 'Unknown'))
        score = row.get('obsolescence_score', 0)
        confidence = row.get('confidence', 0)
        tile_count = row.get('tile_count', 0)
        
        html_content += f"""
                    <tr>
                        <td>{county_name}</td>
                        <td>{state_name}</td>
                        <td>{score:.2f}</td>
                        <td>{confidence:.2f}</td>
                        <td>{tile_count}</td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
        </div>
        
        <div class="container">
            <h2>Bottom 10 Counties by Obsolescence Score</h2>
            <table>
                <thead>
                    <tr>
                        <th>County</th>
                        <th>State</th>
                        <th>Obsolescence Score</th>
                        <th>Confidence</th>
                        <th>Tile Count</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Add bottom counties
    for _, row in bottom_counties.iterrows():
        county_name = row.get('NAME', 'Unknown')
        state_name = row.get('STATE', row.get('STATEFP', 'Unknown'))
        score = row.get('obsolescence_score', 0)
        confidence = row.get('confidence', 0)
        tile_count = row.get('tile_count', 0)
        
        html_content += f"""
                    <tr>
                        <td>{county_name}</td>
                        <td>{state_name}</td>
                        <td>{score:.2f}</td>
                        <td>{confidence:.2f}</td>
                        <td>{tile_count}</td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
        </div>
        
        <footer>
            <p>Generated by LOGhub County Data Report Tool</p>
        </footer>
    </body>
    </html>
    """
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save the HTML report
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"Report saved to {output_file}")

def main():
    """Main function."""
    args = parse_args()
    generate_county_report(args.input, args.output)

if __name__ == "__main__":
    main()
