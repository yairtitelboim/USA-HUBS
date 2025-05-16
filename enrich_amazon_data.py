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

# OpenAI API endpoint
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

def load_amazon_data():
    """Load the existing Amazon fulfillment center data"""
    try:
        with open(AMAZ_JSON_PATH, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading Amazon data: {str(e)}")
        return None

def save_enriched_data(data):
    """Save the enriched data to a new JSON file"""
    try:
        with open(ENRICHED_JSON_PATH, 'w') as file:
            json.dump(data, file, indent=2)
        print(f"Enriched data saved to {ENRICHED_JSON_PATH}")
    except Exception as e:
        print(f"Error saving enriched data: {str(e)}")

def get_facility_details(facility):
    """Generate a detailed description of the facility using OpenAI API"""
    location_details = f"{facility['formatted_address']}"
    if facility.get('city') and facility.get('state'):
        location_details = f"{facility['city']}, {facility['state']}"
    
    facility_id = facility.get('id', 'Unknown')
    facility_type = facility.get('type', 'Fulfillment Center')
    
    # Create the original code from the ID if it exists in the original address
    original_address = facility.get('original_address', '')
    facility_code = ''
    if ' ' in original_address:
        facility_code = original_address.split(' ')[0]
    
    # Build the prompt
    prompt = f"""Please provide factual information about the Amazon {facility_type} facility located at {location_details}. 
If this is facility code {facility_code}, include that information.

Include ONLY real, verifiable information about:
1. Approximate size (square footage) if known
2. Year built or opened
3. Ownership details (owned by Amazon or leased)
4. Key nearby assets (major highways, airports, distribution centers, etc.)
5. Notable features or technologies used in the facility
6. Economic impact on the local area
7. Workforce size if known

Format the response as a JSON object with these fields:
- size_sqft: [numeric or "Unknown"]
- year_built: [year or "Unknown"]
- ownership: ["Owned", "Leased", or "Unknown"]
- nearby_assets: [array of strings]
- features: [array of strings]
- economic_impact: [string]
- workforce: [numeric or "Unknown"]
- facility_code: [string]

If you don't have factual information for any field, use "Unknown" or an empty array.
DO NOT fabricate information. Only include verifiable facts."""

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a logistics and real estate expert who only provides factual information about Amazon fulfillment centers. You never make up information and clearly indicate when data is unavailable."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,  # Use low temperature for more factual responses
            "max_tokens": 800
        }
        
        response = requests.post(OPENAI_API_URL, headers=headers, json=data)
        response.raise_for_status()
        
        response_data = response.json()
        
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            
            # Try to extract JSON from the response
            try:
                # Find JSON within the response if it's wrapped in text or code blocks
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].strip()
                else:
                    json_str = content.strip()
                
                return json.loads(json_str)
            except json.JSONDecodeError:
                print(f"Failed to parse JSON for facility {facility_id}. Response: {content}")
                # Return a basic structure with the original response
                return {
                    "size_sqft": "Unknown",
                    "year_built": "Unknown",
                    "ownership": "Unknown", 
                    "nearby_assets": [],
                    "features": [],
                    "economic_impact": "Unknown",
                    "workforce": "Unknown",
                    "facility_code": facility_code,
                    "raw_response": content
                }
        else:
            print(f"No choices in response for facility {facility_id}")
            return None
    
    except Exception as e:
        print(f"Error getting facility details for {facility_id}: {str(e)}")
        return None

def enrich_amazon_data(amazon_data, limit=None):
    """Enrich Amazon fulfillment center data with details from OpenAI"""
    if not amazon_data or "fulfillment_centers" not in amazon_data:
        print("No valid Amazon data to enrich")
        return None
    
    # Create a copy of the original data
    enriched_data = {
        "fulfillment_centers": [],
        "metadata": amazon_data.get("metadata", {})
    }
    
    # Update metadata
    enriched_data["metadata"]["enriched_date"] = datetime.now().strftime("%Y-%m-%d")
    enriched_data["metadata"]["enrichment_source"] = "OpenAI API"
    
    # Process each fulfillment center
    centers = amazon_data["fulfillment_centers"]
    
    # Limit processing if specified
    if limit and limit > 0:
        centers = centers[:limit]
    
    total = len(centers)
    
    for i, center in enumerate(centers):
        print(f"Processing facility {i+1}/{total}: {center.get('id', 'Unknown')} in {center.get('city', 'Unknown')}")
        
        # Get facility details
        facility_details = get_facility_details(center)
        
        if facility_details:
            # Merge original data with enriched details
            enriched_center = center.copy()
            enriched_center["details"] = facility_details
            enriched_data["fulfillment_centers"].append(enriched_center)
        else:
            # If failed to get details, just use the original data
            enriched_data["fulfillment_centers"].append(center)
        
        # Wait a bit to avoid API rate limits
        if i < total - 1:
            time.sleep(2)
    
    return enriched_data

def main():
    # Load existing Amazon data
    amazon_data = load_amazon_data()
    
    if not amazon_data:
        print("Failed to load Amazon data. Exiting.")
        return
    
    # Ask user for confirmation and optional limit
    print(f"Found {len(amazon_data.get('fulfillment_centers', []))} Amazon facilities.")
    
    try:
        limit_input = input("Enter number of facilities to process (or press Enter for all): ").strip()
        limit = int(limit_input) if limit_input else None
        
        print(f"Starting enrichment process for {'all' if limit is None else limit} facilities...")
        
        # Enrich the data
        enriched_data = enrich_amazon_data(amazon_data, limit)
        
        if enriched_data:
            # Save the enriched data
            save_enriched_data(enriched_data)
            print("Enrichment completed successfully!")
        else:
            print("Enrichment failed. No data to save.")
    
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 