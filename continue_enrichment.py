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
BATCH_SIZE = 5
BATCH_DELAY = 10
REQUEST_DELAY = 3
DEBUG_MODE = True

def debug_print(message):
    """Print debug message if debug mode is enabled"""
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")

def get_facility_details(facility):
    """Get detailed information about a facility using OpenAI"""
    facility_id = facility.get('id', 'Unknown')
    location = f"{facility.get('city', '')}, {facility.get('state', '')}"
    
    # Extract the facility code from the original address (e.g., HSV2, PHX3)
    facility_code = ""
    original_address = facility.get('original_address', '')
    if original_address:
        parts = original_address.split(' ')
        if parts and len(parts[0]) <= 5 and any(c.isdigit() for c in parts[0]):
            facility_code = parts[0]
    
    # Create a detailed prompt instructing OpenAI to use web search
    prompt = f"""You have access to web search. Please search the web for FACTUAL information about Amazon fulfillment center {facility_code} located in {location}.

FIRST, search specifically for "{facility_code} Amazon fulfillment center {location} square footage" to find details about this exact facility.
SECOND, if specific details aren't found, search for "Amazon fulfillment center in {facility.get('city', '')} {facility.get('state', '')}" for general information.
THIRD, search for typical Amazon fulfillment center sizes and features in {facility.get('state', 'the US')} as a reference.

If you cannot find specific details, provide reasonable approximations based on similar Amazon facilities in the same region, but label them as "approximated".
IMPORTANT: Ensure all data is realistic - Amazon fulfillment centers are typically 600,000 to 1,200,000 square feet. Values outside this range or exactly 1 are likely errors.

Provide information on these attributes:
- size_sqft: Size in square feet (realistic number between 600,000-1,200,000)
- year_built: Year when built (between 2000-2023)
- ownership: "Owned" or "Leased" (most facilities are leased)
- nearby_assets: [List of nearby highways, airports, etc]
- features: [List of facility features like robotics, automation, etc]
- economic_impact: Description of jobs/impact on community
- workforce: Number of employees (typically 1,000-3,000)

Format your response as a JSON object like:
{{
  "size_sqft": 800000,
  "size_source": "web" or "approximated",
  "year_built": 2015,
  "year_source": "web" or "approximated",
  "ownership": "Leased",
  "ownership_source": "web" or "approximated",
  "nearby_assets": ["Interstate 10", "Phoenix Sky Harbor Airport"],
  "assets_source": "web" or "approximated",
  "features": ["Robotics", "Automated sorting"],
  "features_source": "web" or "approximated",
  "economic_impact": "Created 1500 jobs in the local community",
  "impact_source": "web" or "approximated",
  "workforce": 1500,
  "workforce_source": "web" or "approximated"
}}

REVIEW your response before submitting to ensure all values are realistic and reasonable. Do not return values like size_sqft = 1 or workforce = 1 which are clearly placeholders."""

    debug_print(f"Sending prompt for {facility_id}")
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a logistics researcher tasked with finding factual information about Amazon facilities. You have access to web search and can look up real information. When you can't find specific details, you should provide reasonable approximations based on similar facilities but clearly mark them as approximated. NEVER return unrealistic values like size_sqft = 1."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "max_tokens": 800
        }
        
        debug_print("Sending request to OpenAI API...")
        response = requests.post(OPENAI_API_URL, headers=headers, json=data)
        
        # Debug API response status
        debug_print(f"API response status: {response.status_code}")
        
        if response.status_code != 200:
            debug_print(f"API error response: {response.text[:200]}...")
            return None
            
        response_data = response.json()
        
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            debug_print(f"Raw API response: {content[:200]}...")
            
            try:
                facility_details = json.loads(content)
                debug_print(f"Parsed JSON successfully")
                return facility_details
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

def has_meaningful_data(details):
    """Check if facility details contain meaningful data with reasonable values"""
    if not details:
        debug_print("Details is None or empty")
        return False
    
    # Check scalar fields with reasonable value validation
    if 'size_sqft' in details:
        size = details['size_sqft']
        if isinstance(size, (int, float)) and 100000 <= size <= 2000000:
            debug_print(f"Found meaningful data in field: size_sqft = {size}")
            return True
        elif size == 1 or (isinstance(size, (int, float)) and size < 100000):
            debug_print(f"Found unreasonable size value: {size}")
            return False
    
    if 'year_built' in details:
        year = details['year_built']
        if isinstance(year, (int, float)) and 2000 <= year <= 2023:
            debug_print(f"Found meaningful data in field: year_built = {year}")
            return True
    
    if 'workforce' in details:
        workforce = details['workforce']
        if isinstance(workforce, (int, float)) and 100 <= workforce <= 5000:
            debug_print(f"Found meaningful data in field: workforce = {workforce}")
            return True
        elif workforce == 1 or (isinstance(workforce, (int, float)) and workforce < 100):
            debug_print(f"Found unreasonable workforce value: {workforce}")
            return False
    
    # Check other scalar fields
    for field in ['ownership', 'economic_impact']:
        if field in details and isinstance(details[field], str) and details[field] not in ["Unknown", ""] and not field.endswith('_source') and len(details[field]) > 10:
            debug_print(f"Found meaningful data in field: {field}")
            return True
    
    # Check array fields
    for field in ['nearby_assets', 'features']:
        if field in details and isinstance(details[field], list) and len(details[field]) >= 2 and not field.endswith('_source'):
            debug_print(f"Found meaningful data in array: {field} = {details[field]}")
            return True
    
    debug_print(f"No meaningful data found")
    return False

def main():
    """Main function"""
    print("=== Amazon Fulfillment Center Enrichment (Web-Enabled) ===")
    
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
    except Exception as e:
        print(f"✗ OpenAI API connection test error: {str(e)}")
    
    # Load original and enriched data
    try:
        with open(AMAZ_JSON_PATH, 'r') as file:
            original_data = json.load(file)
            print(f"Loaded original data with {len(original_data.get('fulfillment_centers', []))} facilities")
        
        try:
            # Try to load existing enriched data, but don't fail if it doesn't exist
            with open(ENRICHED_JSON_PATH, 'r') as file:
                enriched_data = json.load(file)
                print(f"Loaded existing enriched data with {len(enriched_data.get('fulfillment_centers', []))} facilities")
        except (FileNotFoundError, json.JSONDecodeError):
            # If enriched file doesn't exist or is invalid, start fresh with original data
            print("No valid enriched data found, starting fresh")
            enriched_data = {
                "fulfillment_centers": [],
                "metadata": {
                    "created_date": datetime.now().strftime("%Y-%m-%d"),
                    "web_search_enabled": True
                }
            }
    except Exception as e:
        print(f"Error loading original data: {str(e)}")
        return
    
    # Create a mapping of enriched centers by ID
    enriched_map = {}
    for center in enriched_data.get('fulfillment_centers', []):
        if 'id' in center:
            enriched_map[center['id']] = center
    
    # Process all original centers, keeping existing enriched data
    all_centers = []
    for center in original_data.get('fulfillment_centers', []):
        if center.get('id') in enriched_map:
            # Use existing enriched data if available
            all_centers.append(enriched_map[center.get('id')])
        else:
            # Otherwise use original data, adding an empty details field
            new_center = center.copy()
            new_center['details'] = {
                "size_sqft": "Unknown",
                "year_built": "Unknown",
                "ownership": "Unknown",
                "nearby_assets": [],
                "features": [],
                "economic_impact": "Unknown",
                "workforce": "Unknown"
            }
            all_centers.append(new_center)
    
    # Replace fulfillment_centers with our merged list
    enriched_data['fulfillment_centers'] = all_centers
    
    # Find facilities that need enrichment
    need_enrichment = []
    for center in enriched_data.get('fulfillment_centers', []):
        if not has_meaningful_data(center.get('details', {})):
            need_enrichment.append(center)
    
    print(f"Found {len(need_enrichment)} facilities that need enrichment out of {len(all_centers)} total")
    
    # Ask user if they want to continue
    max_to_process = int(input(f"Enter the maximum number to process (or 0 for all): ") or "0")
    if max_to_process == 0:
        max_to_process = len(need_enrichment)
    
    to_process = need_enrichment[:max_to_process]
    print(f"Will process {len(to_process)} facilities")
    
    # Process in batches
    enriched_count = 0
    
    for i in range(0, len(to_process), BATCH_SIZE):
        batch = to_process[i:i+BATCH_SIZE]
        print(f"\nProcessing batch {i//BATCH_SIZE + 1} ({i}-{min(i+BATCH_SIZE-1, len(to_process)-1)})")
        
        for center in batch:
            center_id = center.get('id', 'Unknown')
            print(f"Processing {center_id} in {center.get('city', 'Unknown')}, {center.get('state', 'Unknown')}")
            
            # Get new details
            new_details = get_facility_details(center)
            
            if new_details is None:
                print(f"✗ Failed to get data for {center_id}")
                continue
                
            if has_meaningful_data(new_details):
                print(f"✓ Found meaningful data for {center_id}")
                enriched_count += 1
            else:
                print(f"✗ No meaningful data found for {center_id}")
            
            # Update the center in our enriched data
            for idx, enriched_center in enumerate(enriched_data['fulfillment_centers']):
                if enriched_center.get('id') == center_id:
                    enriched_data['fulfillment_centers'][idx]['details'] = new_details
                    break
            
            # Wait between requests
            print(f"Waiting {REQUEST_DELAY} seconds before next request...")
            time.sleep(REQUEST_DELAY)
        
        # Save progress after each batch
        try:
            backup_path = f"county-viz-app/public/data/final/Hubs/AMAZ_enriched_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
    
    # Add metadata 
    enriched_data['metadata'] = enriched_data.get('metadata', {})
    enriched_data['metadata']['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    enriched_data['metadata']['web_search_enabled'] = True
    enriched_data['metadata']['total_facilities'] = len(enriched_data['fulfillment_centers'])
    
    # Save final data
    with open(ENRICHED_JSON_PATH, 'w') as file:
        json.dump(enriched_data, file, indent=2)
    
    # Print summary
    print("\n=== Enrichment Summary ===")
    print(f"Processed {len(to_process)} facilities")
    print(f"Successfully enriched {enriched_count} facilities")
    
    # Count total meaningful data
    total_enriched = 0
    for center in enriched_data.get('fulfillment_centers', []):
        if has_meaningful_data(center.get('details', {})):
            total_enriched += 1
    
    total = len(enriched_data.get('fulfillment_centers', []))
    print(f"\nTotal facilities with meaningful data: {total_enriched}/{total} ({total_enriched/total*100:.2f}%)")
    print(f"Facilities without meaningful data: {total-total_enriched}/{total} ({(total-total_enriched)/total*100:.2f}%)")

if __name__ == "__main__":
    main()