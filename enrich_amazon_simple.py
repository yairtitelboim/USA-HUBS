#!/usr/bin/env python3
import os
import json
import time
import requests
from datetime import datetime

# Configuration
AMAZ_JSON_PATH = "county-viz-app/public/data/final/Hubs/AMAZ.json"
ENRICHED_JSON_PATH = "county-viz-app/public/data/final/Hubs/AMAZ_enriched.json"
OPENAI_API_KEY = "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"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Processing settings
BATCH_SIZE = 3  # Process this many at once
BATCH_DELAY = 5  # Wait this many seconds between batches
REQUEST_DELAY = 2  # Wait this many seconds between requests

def log_message(message):
    """Print log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def get_facility_details(facility):
    """Generate details for a facility using OpenAI API"""
    location = f"{facility['city']}, {facility['state']}" if facility.get('city') and facility.get('state') else facility.get('formatted_address', 'Unknown')
    facility_id = facility.get('id', 'Unknown')
    
    # Create prompt for OpenAI
    prompt = f"""Return ONLY factual information about Amazon fulfillment center {facility_id} in {location}.
Format as JSON with these fields:
- size_sqft: number or "Unknown"
- year_built: number or "Unknown" 
- ownership: "Owned", "Leased", or "Unknown"
- nearby_assets: [list of nearby highways, airports, etc] or []
- features: [list of notable facility features] or []
- economic_impact: string or "Unknown"
- workforce: number or "Unknown"

DO NOT invent information. Only return the JSON."""

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a logistics researcher who only provides factual information about Amazon facilities."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(OPENAI_API_URL, headers=headers, json=data)
        response.raise_for_status()
        
        response_data = response.json()
        
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            facility_details = json.loads(content)
            return facility_details
        else:
            return {
                "size_sqft": "Unknown",
                "year_built": "Unknown",
                "ownership": "Unknown",
                "nearby_assets": [],
                "features": [],
                "economic_impact": "Unknown",
                "workforce": "Unknown"
            }
    
    except Exception as e:
        log_message(f"Error getting details for {facility_id}: {str(e)}")
        return {
            "size_sqft": "Unknown",
            "year_built": "Unknown",
            "ownership": "Unknown",
            "nearby_assets": [],
            "features": [],
            "economic_impact": "Unknown",
            "workforce": "Unknown"
        }

def main():
    """Main function for Amazon data enrichment"""
    log_message("Starting Amazon data enrichment")
    
    # Load original data
    try:
        with open(AMAZ_JSON_PATH, 'r') as file:
            amazon_data = json.load(file)
            total = len(amazon_data.get('fulfillment_centers', []))
            log_message(f"Loaded {total} Amazon facilities")
    except Exception as e:
        log_message(f"Error loading data: {str(e)}")
        return
    
    # Check for existing enriched data
    enriched_data = None
    try:
        if os.path.exists(ENRICHED_JSON_PATH):
            with open(ENRICHED_JSON_PATH, 'r') as file:
                enriched_data = json.load(file)
                log_message(f"Loaded existing enriched data with {len(enriched_data.get('fulfillment_centers', []))} facilities")
    except Exception as e:
        log_message(f"Error loading existing enriched data: {str(e)}")
    
    # Create mapping of enriched facilities
    enriched_map = {}
    if enriched_data and 'fulfillment_centers' in enriched_data:
        for center in enriched_data['fulfillment_centers']:
            if 'id' in center:
                enriched_map[center['id']] = center
    
    # Create new enriched data
    new_enriched_data = {
        "fulfillment_centers": [],
        "metadata": {
            "enriched_date": datetime.now().strftime("%Y-%m-%d"),
            "enrichment_source": "OpenAI API",
            "original_count": total
        }
    }
    
    # Process in batches
    centers = amazon_data.get('fulfillment_centers', [])
    enriched_count = 0
    skipped_count = 0
    
    # Process a subset for testing - change this to process more
    # Comment out the next line to process all facilities
    centers = centers[:10]  # Process only 10 for testing
    
    log_message(f"Will process {len(centers)} facilities")
    
    for i in range(0, len(centers), BATCH_SIZE):
        batch = centers[i:i+BATCH_SIZE]
        log_message(f"Processing batch {i//BATCH_SIZE + 1} ({i}-{min(i+BATCH_SIZE-1, len(centers)-1)})")
        
        for center in batch:
            center_id = center.get('id', 'Unknown')
            
            # Check if already have good data
            if center_id in enriched_map:
                log_message(f"Facility {center_id} already enriched, skipping")
                new_enriched_data["fulfillment_centers"].append(enriched_map[center_id])
                skipped_count += 1
                continue
            
            log_message(f"Processing facility {center_id} in {center.get('city', 'Unknown')}")
            
            # Get details
            details = get_facility_details(center)
            
            # Add to enriched data
            enriched_center = center.copy()
            enriched_center["details"] = details
            new_enriched_data["fulfillment_centers"].append(enriched_center)
            
            # Check if we got meaningful data
            has_data = False
            for field in ['size_sqft', 'year_built', 'ownership', 'workforce', 'economic_impact']:
                if field in details and details[field] != "Unknown":
                    has_data = True
                    break
            
            for field in ['nearby_assets', 'features']:
                if field in details and len(details[field]) > 0:
                    has_data = True
                    break
            
            if has_data:
                enriched_count += 1
                log_message(f"Added meaningful data for {center_id}")
            
            # Wait between requests
            time.sleep(REQUEST_DELAY)
        
        # Save progress after each batch
        try:
            with open(ENRICHED_JSON_PATH, 'w') as file:
                json.dump(new_enriched_data, file, indent=2)
            log_message(f"Saved progress with {len(new_enriched_data['fulfillment_centers'])} facilities")
        except Exception as e:
            log_message(f"Error saving progress: {str(e)}")
        
        # Wait between batches
        if i + BATCH_SIZE < len(centers):
            log_message(f"Waiting {BATCH_DELAY} seconds before next batch")
            time.sleep(BATCH_DELAY)
    
    # Save final data
    try:
        with open(ENRICHED_JSON_PATH, 'w') as file:
            json.dump(new_enriched_data, file, indent=2)
        log_message(f"Saved enriched data with {len(new_enriched_data['fulfillment_centers'])} facilities")
    except Exception as e:
        log_message(f"Error saving final data: {str(e)}")
    
    log_message(f"Enrichment complete!")
    log_message(f"Added meaningful data to {enriched_count} new facilities")
    log_message(f"Skipped {skipped_count} already-enriched facilities")

if __name__ == "__main__":
    main() 