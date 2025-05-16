#!/usr/bin/env python3
import json
import pprint

# Load the enriched data
try:
    file_path = 'county-viz-app/public/data/final/Hubs/AMAZ_enriched.json'
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    total = len(data['fulfillment_centers'])
    
    # Find centers with meaningful data
    enriched_centers = []
    for center in data['fulfillment_centers']:
        if 'details' not in center:
            continue
            
        details = center['details']
        has_real_data = False
        
        # Check for non-empty data
        for field in ['size_sqft', 'year_built', 'ownership', 'workforce', 'economic_impact']:
            if field in details and details[field] != "Unknown":
                has_real_data = True
                break
        
        for field in ['nearby_assets', 'features']:
            if field in details and len(details[field]) > 0:
                has_real_data = True
                break
        
        if has_real_data:
            enriched_centers.append(center)
    
    # Print a few examples of enriched centers
    print(f"Found {len(enriched_centers)} enriched centers out of {total} total")
    
    # Print 3 examples
    examples_to_show = min(3, len(enriched_centers))
    
    for i in range(examples_to_show):
        center = enriched_centers[i]
        print(f"\n{'='*50}")
        print(f"Example {i+1}: {center['id']} - {center['city']}, {center['state']}")
        print(f"{'='*50}")
        
        details = center['details']
        
        # Print all non-empty fields
        for field in ['size_sqft', 'year_built', 'ownership', 'workforce', 'economic_impact']:
            if field in details and details[field] != "Unknown":
                print(f"{field}: {details[field]}")
        
        for field in ['nearby_assets', 'features']:
            if field in details and len(details[field]) > 0:
                print(f"{field}: {', '.join(details[field])}")
                
except Exception as e:
    print(f"Error analyzing examples: {str(e)}") 