#!/usr/bin/env python3
import json
import os

# Load the enriched data
try:
    file_path = 'county-viz-app/public/data/final/Hubs/AMAZ_enriched.json'
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    total = len(data['fulfillment_centers'])
    enriched_count = 0
    
    # Statistics for different fields
    unknown_fields = {
        'size_sqft': 0,
        'year_built': 0, 
        'ownership': 0,
        'workforce': 0,
        'economic_impact': 0
    }
    
    empty_arrays = {
        'nearby_assets': 0,
        'features': 0
    }
    
    # Count enriched locations
    for center in data['fulfillment_centers']:
        if 'details' in center:
            details = center['details']
            has_real_data = False
            
            # Check scalar fields
            for field in unknown_fields.keys():
                if field in details and details[field] != "Unknown":
                    has_real_data = True
                else:
                    unknown_fields[field] += 1
            
            # Check array fields
            for array_field in empty_arrays.keys():
                if array_field in details and len(details[array_field]) > 0:
                    has_real_data = True
                else:
                    empty_arrays[array_field] += 1
            
            if has_real_data:
                enriched_count += 1
    
    # Print results
    print(f'Total Amazon locations: {total}')
    print(f'Locations with meaningful enriched data: {enriched_count} ({enriched_count/total*100:.2f}%)')
    print(f'Locations without meaningful data: {total-enriched_count} ({(total-enriched_count)/total*100:.2f}%)')
    
    print('\nField statistics:')
    for field, count in unknown_fields.items():
        print(f'{field}: {count} unknown ({count/total*100:.2f}%)')
    
    for field, count in empty_arrays.items():
        print(f'{field}: {count} empty ({count/total*100:.2f}%)')
        
except Exception as e:
    print(f"Error analyzing enrichment data: {str(e)}") 