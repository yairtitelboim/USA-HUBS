#!/usr/bin/env python3
import os
import json
import time
import requests
from datetime import datetime

# Configuration
AMAZ_JSON_PATH = "county-viz-app/public/data/final/Hubs/AMAZ.json"
ENRICHED_JSON_PATH = "county-viz-app/public/data/final/Hubs/AMAZ_enriched.json"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Settings
BATCH_SIZE = 10  # Process more facilities at once
BATCH_DELAY = 5
REQUEST_DELAY = 2
DEBUG_MODE = True

# Size validation constants
MIN_REASONABLE_SIZE = 200000  # 200,000 sq ft minimum
MAX_REASONABLE_SIZE = 1500000  # 1.5 million sq ft maximum

def debug_print(message):
    """Print debug message if debug mode is enabled"""
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")

def get_facility_size(facility):
    """Get detailed size information about a facility using OpenAI"""
    facility_id = facility.get('id', 'Unknown')
    location = f"{facility.get('city', '')}, {facility.get('state', '')}"
    
    # Extract the facility code from the original address (e.g., HSV2, PHX3)
    facility_code = ""
    original_address = facility.get('original_address', '')
    if original_address:
        parts = original_address.split(' ')
        if parts and len(parts[0]) <= 5 and any(c.isdigit() for c in parts[0]):
            facility_code = parts[0]
    
    facility_type = facility.get('type', 'Fulfillment Center')
    
    # Create a focused prompt instructing OpenAI to search specifically for size information
    prompt = f"""You have access to web search. Your task is to find the SQUARE FOOTAGE or SIZE of the following Amazon facility using web search:

FACILITY DETAILS:
- ID/Code: {facility_code}
- City: {facility.get('city', '')}
- State: {facility.get('state', '')}
- Type: {facility_type}
- Address: {facility.get('formatted_address', '')}

SUCCESSFUL EXAMPLES OF RESPONSES:
Example 1 (when you find exact information):
{{
  "size_sqft": 855000,
  "size_source": "web",
  "confidence": "high",
  "search_notes": "Found in Seattle Times article about facility opening in 2021"
}}

Example 2 (when you need to approximate):
{{
  "size_sqft": 650000,
  "size_source": "approximated",
  "confidence": "medium",
  "search_notes": "Based on typical Amazon fulfillment center in this region; news articles mention it's a standard-sized facility"
}}

FACILITY TYPE SIZE GUIDELINES (use when approximating):
- Fulfillment Centers: 600,000 to 1,000,000 sq ft
- Sortation Centers: 300,000 to 400,000 sq ft
- Delivery Stations: 100,000 to 200,000 sq ft
- Air Hubs: 800,000 to 3,000,000 sq ft

SEARCH INSTRUCTIONS:
1. First search: "{facility_code} Amazon {facility.get('city', '')} {facility.get('state', '')} square footage"
2. Second search: "Amazon {facility_type} {location} size square feet"
3. Third search: "Amazon {location} warehouse size"

CRITICAL RULES:
1. The size_sqft MUST be a reasonable number between {MIN_REASONABLE_SIZE} and {MAX_REASONABLE_SIZE}
2. DO NOT return "size_sqft": 1 or any placeholder values
3. If you can't find the exact size, use the facility type guidelines to make a reasonable approximation
4. ALWAYS use a value in the range of {MIN_REASONABLE_SIZE} to {MAX_REASONABLE_SIZE}
5. If approximating, choose a typical value for the facility type (e.g., 800,000 for a Fulfillment Center)

Return ONLY the JSON object with these fields: size_sqft, size_source, confidence, and search_notes."""

    debug_print(f"Searching for size data for {facility_id}")
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a logistics researcher specializing in Amazon facility data. Your sole task is to find accurate square footage information for Amazon facilities. You MUST provide realistic size values (no placeholders like 1). If exact data is unavailable, provide a reasonable estimate based on facility type."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "max_tokens": 500
        }
        
        debug_print("Sending request to OpenAI API...")
        response = requests.post(OPENAI_API_URL, headers=headers, json=data)
        
        if response.status_code != 200:
            debug_print(f"API error response: {response.text[:200]}...")
            return None
            
        response_data = response.json()
        
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            # Log the full response for debugging
            debug_print(f"Raw API response: {content}")
            
            try:
                size_data = json.loads(content)
                
                # Validate size is reasonable
                if "size_sqft" in size_data:
                    size = size_data["size_sqft"]
                    if not isinstance(size, (int, float)) or size < MIN_REASONABLE_SIZE or size > MAX_REASONABLE_SIZE:
                        debug_print(f"Unreasonable size value: {size}")
                        if size == 1:
                            debug_print(f"Placeholder value detected. The model is not providing a proper estimate!")
                        return None
                    
                    debug_print(f"Found size: {size} sq ft ({size_data.get('size_source', 'unknown source')})")
                    return size_data
                else:
                    debug_print("No size_sqft field in response")
                    return None
                    
            except json.JSONDecodeError as e:
                debug_print(f"JSON parse error: {str(e)}")
                return None
        else:
            debug_print(f"No choices in response")
            return None
            
    except Exception as e:
        debug_print(f"Exception: {str(e)}")
        return None
    
    return None

def needs_size_enrichment(facility):
    """Check if facility needs size enrichment"""
    details = facility.get('details', {})
    
    # Facility needs enrichment if:
    # 1. No details field
    if not details:
        return True
        
    # 2. No size_sqft field
    if 'size_sqft' not in details:
        return True
        
    # 3. size_sqft is "Unknown" string
    if details['size_sqft'] == "Unknown":
        return True
        
    # 4. size_sqft is unreasonably small (like 1) or outside valid range
    if isinstance(details['size_sqft'], (int, float)):
        if details['size_sqft'] < MIN_REASONABLE_SIZE or details['size_sqft'] > MAX_REASONABLE_SIZE:
            return True
    
    # Otherwise, it doesn't need enrichment
    return False

def update_facility_size(facility, size_data):
    """Update facility with new size information"""
    if 'details' not in facility:
        facility['details'] = {}
    
    facility['details']['size_sqft'] = size_data['size_sqft']
    facility['details']['size_source'] = size_data['size_source']
    
    if 'confidence' in size_data:
        facility['details']['size_confidence'] = size_data['confidence']
    
    if 'search_notes' in size_data:
        facility['details']['size_notes'] = size_data['search_notes']
    
    return facility

def estimate_facility_size(facility):
    """Provide a reasonable size estimate based on facility type when API fails"""
    facility_type = facility.get('type', 'Fulfillment Center').lower()
    
    # Default size ranges by facility type
    size_ranges = {
        'fulfillment center': (600000, 1000000),
        'sortation center': (300000, 400000),
        'delivery station': (100000, 200000),
        'air hub': (800000, 3000000),
        'return center': (300000, 500000),
        'pantry facility': (400000, 600000),
        'robotics facility': (800000, 1200000)
    }
    
    # Get the appropriate range
    for key, (min_size, max_size) in size_ranges.items():
        if key in facility_type.lower():
            # Return a value in the middle of the range
            return {
                "size_sqft": int((min_size + max_size) / 2),
                "size_source": "estimated",
                "confidence": "low",
                "search_notes": f"Estimated based on typical size for {facility_type}"
            }
    
    # Default to fulfillment center if no match
    return {
        "size_sqft": 800000,  # Middle of the range for fulfillment centers
        "size_source": "estimated",
        "confidence": "low",
        "search_notes": "Estimated using default size for Amazon facilities"
    }

def process_facility_with_retry(center, max_retries=2):
    """Process a facility with retry capability"""
    center_id = center.get('id', 'Unknown')
    print(f"Processing {center_id} in {center.get('city', 'Unknown')}, {center.get('state', 'Unknown')}")
    
    for attempt in range(max_retries + 1):
        if attempt > 0:
            print(f"Retry attempt {attempt}/{max_retries}...")
            
        # Get size information
        size_data = get_facility_size(center)
        
        if size_data is not None:
            # Update the facility with new size data
            updated_center = update_facility_size(center, size_data)
            print(f"✓ Updated size for {center_id}: {size_data['size_sqft']} sq ft ({size_data.get('size_source', 'unknown')})")
            return updated_center, True
            
        if attempt < max_retries:
            print(f"Waiting {REQUEST_DELAY*2} seconds before retry...")
            time.sleep(REQUEST_DELAY*2)
    
    # After all retries failed, use the estimator
    print(f"✗ Failed to get size data from API for {center_id} after {max_retries+1} attempts")
    print(f"Using fallback size estimator...")
    
    # Use the estimator function
    estimated_size = estimate_facility_size(center)
    updated_center = update_facility_size(center, estimated_size)
    print(f"✓ Added estimated size for {center_id}: {estimated_size['size_sqft']} sq ft (estimated)")
    
    return updated_center, True

def main():
    """Main function for size enrichment"""
    print("=== Amazon Facility Size Enrichment ===")
    
    # Test API connection
    print("Testing OpenAI API connection...")
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        test_data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "user", "content": "Respond with 'connected' if you can see this message."}
            ],
            "max_tokens": 50
        }
        
        response = requests.post(OPENAI_API_URL, headers=headers, json=test_data)
        if response.status_code == 200:
            print("✓ OpenAI API connection successful")
        else:
            print(f"✗ OpenAI API connection failed: {response.status_code}")
            return
    except Exception as e:
        print(f"✗ OpenAI API connection test error: {str(e)}")
        return
    
    # Load data
    try:
        # Load original data for reference
        with open(AMAZ_JSON_PATH, 'r') as file:
            original_data = json.load(file)
            print(f"Loaded original data with {len(original_data.get('fulfillment_centers', []))} facilities")
        
        # Load enriched data that we'll update
        with open(ENRICHED_JSON_PATH, 'r') as file:
            enriched_data = json.load(file)
            print(f"Loaded enriched data with {len(enriched_data.get('fulfillment_centers', []))} facilities")
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return
    
    # Find facilities that need size enrichment
    need_enrichment = []
    for center in enriched_data.get('fulfillment_centers', []):
        if needs_size_enrichment(center):
            need_enrichment.append(center)
    
    print(f"Found {len(need_enrichment)} facilities that need size enrichment out of {len(enriched_data.get('fulfillment_centers', []))} total")
    
    # Ask user how many to process
    max_to_process = int(input(f"Enter the maximum number to process (or 0 for all): ") or "0")
    if max_to_process == 0:
        max_to_process = len(need_enrichment)
    
    to_process = need_enrichment[:max_to_process]
    print(f"Will process {len(to_process)} facilities")
    
    # Process in batches
    enriched_count = 0
    failed_count = 0
    
    for i in range(0, len(to_process), BATCH_SIZE):
        batch = to_process[i:i+BATCH_SIZE]
        print(f"\nProcessing batch {i//BATCH_SIZE + 1} ({i}-{min(i+BATCH_SIZE-1, len(to_process)-1)})")
        
        for center in batch:
            center_id = center.get('id', 'Unknown')
            
            # Process with retry capability
            updated_center, success = process_facility_with_retry(center)
            
            if success:
                enriched_count += 1
                
                # Update the enriched data with the modified facility
                for idx, enriched_center in enumerate(enriched_data['fulfillment_centers']):
                    if enriched_center.get('id') == center_id:
                        enriched_data['fulfillment_centers'][idx] = updated_center
                        break
            else:
                failed_count += 1
            
            # Wait between requests
            if center != batch[-1]:  # Don't wait after last item in batch
                print(f"Waiting {REQUEST_DELAY} seconds before next request...")
                time.sleep(REQUEST_DELAY)
        
        # Save progress after each batch
        try:
            backup_path = f"county-viz-app/public/data/final/Hubs/AMAZ_enriched_size_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_path, 'w') as file:
                json.dump(enriched_data, file, indent=2)
            print(f"Created backup at {backup_path}")
            
            with open(ENRICHED_JSON_PATH, 'w') as file:
                json.dump(enriched_data, file, indent=2)
            print(f"Saved progress")
        except Exception as e:
            print(f"Error saving: {str(e)}")
        
        # Wait between batches
        if i + BATCH_SIZE < len(to_process):
            print(f"Waiting {BATCH_DELAY} seconds before next batch")
            time.sleep(BATCH_DELAY)
    
    # Update metadata
    enriched_data['metadata'] = enriched_data.get('metadata', {})
    enriched_data['metadata']['size_enrichment_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    enriched_data['metadata']['size_enrichment_count'] = enriched_count
    
    # Save final data
    with open(ENRICHED_JSON_PATH, 'w') as file:
        json.dump(enriched_data, file, indent=2)
    
    # Print summary
    print("\n=== Size Enrichment Summary ===")
    print(f"Processed {len(to_process)} facilities")
    print(f"Successfully enriched: {enriched_count}")
    print(f"Failed: {failed_count}")
    
    # Count facilities with valid size
    valid_size_count = 0
    for center in enriched_data.get('fulfillment_centers', []):
        details = center.get('details', {})
        if 'size_sqft' in details and isinstance(details['size_sqft'], (int, float)) and MIN_REASONABLE_SIZE <= details['size_sqft'] <= MAX_REASONABLE_SIZE:
            valid_size_count += 1
    
    total = len(enriched_data.get('fulfillment_centers', []))
    print(f"\nFacilities with valid size data: {valid_size_count}/{total} ({valid_size_count/total*100:.1f}%)")
    print(f"Facilities without valid size data: {total-valid_size_count}/{total} ({(total-valid_size_count)/total*100:.1f}%)")

if __name__ == "__main__":
    main() 