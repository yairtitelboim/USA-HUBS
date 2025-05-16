#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script to verify that all required libraries are installed correctly.
"""

import sys
import os

def test_imports():
    """Test importing all required libraries."""
    libraries = [
        "torch", "torchvision", "transformers", "geopandas", 
        "networkx", "xgboost", "rasterio", "mapboxgl"
    ]
    
    success = True
    for lib in libraries:
        try:
            __import__(lib)
            print(f"✅ Successfully imported {lib}")
        except ImportError as e:
            print(f"❌ Failed to import {lib}: {e}")
            success = False
    
    return success

def test_torch():
    """Test PyTorch functionality."""
    import torch
    
    # Create a simple tensor
    x = torch.rand(5, 3)
    print(f"\nPyTorch test tensor:\n{x}")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    return True

def test_transformers():
    """Test Transformers library."""
    from transformers import AutoTokenizer
    
    # Initialize a tokenizer
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased", local_files_only=False)
    text = "Testing the transformers library."
    tokens = tokenizer(text, return_tensors="pt")
    
    print(f"\nTransformers tokenization test:")
    print(f"Original text: {text}")
    print(f"Tokenized: {tokens}")
    
    return True

def test_geopandas():
    """Test GeoPandas functionality."""
    import geopandas as gpd
    from shapely.geometry import Point
    
    # Create a simple GeoDataFrame
    points = [Point(0, 0), Point(1, 1)]
    gdf = gpd.GeoDataFrame(geometry=points)
    
    print(f"\nGeoPandas test GeoDataFrame:\n{gdf}")
    
    return True

def test_networkx():
    """Test NetworkX functionality."""
    import networkx as nx
    
    # Create a simple graph
    G = nx.Graph()
    G.add_edges_from([(1, 2), (1, 3), (2, 3), (3, 4)])
    
    print(f"\nNetworkX test graph:")
    print(f"Nodes: {G.nodes()}")
    print(f"Edges: {G.edges()}")
    
    return True

def test_xgboost():
    """Test XGBoost functionality."""
    import xgboost as xgb
    import numpy as np
    
    # Create a simple DMatrix
    data = np.random.rand(5, 10)
    label = np.random.randint(2, size=5)
    dtrain = xgb.DMatrix(data, label=label)
    
    print(f"\nXGBoost test DMatrix:")
    print(f"DMatrix shape: {dtrain.num_row()} rows, {dtrain.num_col()} columns")
    
    return True

def main():
    """Run all tests."""
    print("Testing Python environment...\n")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print("\nTesting library imports:")
    
    if not test_imports():
        print("\n❌ Some libraries failed to import. Please check the error messages above.")
        return
    
    # Run individual library tests
    try:
        test_torch()
        test_transformers()
        test_geopandas()
        test_networkx()
        test_xgboost()
        
        print("\n✅ All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
