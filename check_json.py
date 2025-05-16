import json
import sys

try:
    with open('data/final/county_scores.geojson', 'r') as f:
        data = json.load(f)
    print(f"File is valid JSON with {len(data['features'])} features")
except json.JSONDecodeError as e:
    print(f"JSON error at line {e.lineno}, column {e.colno}: {e.msg}")
    
    # Try to find the exact location of the error
    with open('data/final/county_scores.geojson', 'r') as f:
        lines = f.readlines()
    
    # Print the problematic line and a few lines before and after
    start_line = max(0, e.lineno - 3)
    end_line = min(len(lines), e.lineno + 3)
    
    print("\nContext around error:")
    for i in range(start_line, end_line):
        prefix = ">>> " if i == e.lineno - 1 else "    "
        print(f"{prefix}Line {i+1}: {lines[i].rstrip()}")
        
        # If this is the error line, add a pointer to the error position
        if i == e.lineno - 1:
            print(" " * (len(prefix) + len(f"Line {i+1}: ") + e.colno) + "^")
