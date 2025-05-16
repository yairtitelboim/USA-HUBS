#!/usr/bin/env python3
import os
import json
import time
import requests
import random
import sys
from datetime import datetime

# Configuration
AMAZ_JSON_PATH = "county-viz-app/public/data/final/Hubs/AMAZ.json"
ENRICHED_JSON_PATH = "county-viz-app/public/data/final/Hubs/AMAZ_enriched.json"
TEMP_BACKUP_PATH = "county-viz-app/public/data/final/Hubs/AMAZ_enriched_backup.json"
ERROR_LOG_PATH = "amazon_enrichment_errors.log"
OPENAI_API_KEY = "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"

# OpenAI API endpoint
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Batch processing settings
BATCH_SIZE = 5  # Process this many facilities at once
BATCH_DELAY = 10  # Wait this many seconds between batches
FACILITY_DELAY = 2  # Wait this many seconds between individual facilities

# Modifiable settings
DEFAULT_MAX_RETRIES = 2 
DEFAULT_RETRY_DELAY = 5

# Setup logging
def log_error(message):
    """Write error message to log file"""
    with open(ERROR_LOG_PATH, 'a') as log_file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"[{timestamp}] {message}\n")
    print(f"ERROR: {message}")

def load_amazon_data():
    """Load the existing Amazon fulfillment center data"""
    try:
        with open(AMAZ_JSON_PATH, 'r') as file:
            return json.load(file)
    except Exception as e:
        log_error(f"Error loading Amazon data: {str(e)}")
        return None

def load_existing_enriched_data():
    """Load any existing enriched data file if it exists"""
    try:
        if os.path.exists(ENRICHED_JSON_PATH):
            with open(ENRICHED_JSON_PATH, 'r') as file:
                return json.load(file)
        return None
    except Exception as e:
        log_error(f"Error loading existing enriched data: {str(e)}")
        return None

def save_enriched_data(data):
    """Save the enriched data to a JSON file with backup"""
    try:
        # First backup any existing file
        if os.path.exists(ENRICHED_JSON_PATH):
            with open(ENRICHED_JSON_PATH, 'r') as source:
                with open(TEMP_BACKUP_PATH, 'w') as target:
                    target.write(source.read())
            print(f"Backup created at {TEMP_BACKUP_PATH}")
        
        # Now save the new data
        with open(ENRICHED_JSON_PATH, 'w') as file:
            json.dump(data, file, indent=2)
        print(f"Enriched data saved to {ENRICHED_JSON_PATH}")
    except Exception as e:
        log_error(f"Error saving enriched data: {str(e)}")

def save_progress(data, progress_count):
    """Save current progress"""
    try:
        progress_path = f"county-viz-app/public/data/final/Hubs/AMAZ_enriched_progress_{progress_count}.json"
        with open(progress_path, 'w') as file:
            json.dump(data, file, indent=2)
        print(f"Progress saved to {progress_path}")
    except Exception as e:
        log_error(f"Error saving progress: {str(e)}")

def get_facility_details(facility, max_retries=DEFAULT_MAX_RETRIES):
    """Generate a detailed description of the facility using OpenAI API with enhanced prompting and retries"""
    location_details = f"{facility['formatted_address']}"
    if facility.get('city') and facility.get('state'):
        location_details = f"{facility['city']}, {facility['state']}"
    
    facility_id = facility.get('id', 'Unknown')
    facility_type = facility.get('type', 'Fulfillment Center')
    
    # Create the facility code from the ID if it exists in the original address
    original_address = facility.get('original_address', '')
    facility_code = ''
    if ' ' in original_address:
        facility_code = original_address.split(' ')[0]
    
    # Build the improved prompt - shorter, more precise, emphasis on verified info
    prompt = f"""I need ONLY factual information about the Amazon {facility_type} (ID: {facility_id}) located in {location_details}.
If this has facility code {facility_code}, include that.

Return ONLY verifiable facts about:
1. Size (square footage) 
2. Year built/opened
3. Ownership (owned/leased)
4. Nearby assets (highways, airports)
5. Notable features (robotics, automation)
6. Economic impact (jobs created)
7. Approximate workforce size

Format response as JSON with these fields (use "Unknown" for unavailable data, EMPTY arrays for unknown lists):
{{
  "size_sqft": number or "Unknown",
  "year_built": number or "Unknown",
  "ownership": "Owned", "Leased", or "Unknown",
  "nearby_assets": [list of strings],
  "features": [list of strings],
  "economic_impact": string or "Unknown",
  "workforce": number or "Unknown",
  "facility_code": string or "Unknown"
}}

DO NOT invent information. If you don't know, use "Unknown" or empty arrays. Return ONLY the JSON object, nothing else."""

    retries = 0
    while retries <= max_retries:
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            data = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "You are a logistics research assistant providing only factual information about Amazon facilities. You never make up information and clearly indicate when data is unavailable. Provide JSON responses only, no explanations or additional text."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,  # Very low temperature for factual responses
                "response_format": {"type": "json_object"},  # Enforce JSON format
                "max_tokens": 500
            }
            
            response = requests.post(OPENAI_API_URL, headers=headers, json=data)
            response.raise_for_status()
            
            response_data = response.json()
            
            if "choices" in response_data and response_data["choices"]:
                content = response_data["choices"][0]["message"]["content"]
                
                # Try to extract clean JSON
                try:
                    facility_details = json.loads(content)
                    return facility_details
                except json.JSONDecodeError as e:
                    log_error(f"Failed to parse JSON for facility {facility_id}. Response: {content[:100]}... Error: {str(e)}")
                    # Try one more time with content cleaning
                    try:
                        # Try to extract JSON if wrapped in code blocks
                        if "```json" in content:
                            clean_content = content.split("```json")[1].split("```")[0].strip()
                        elif "```" in content:
                            clean_content = content.split("```")[1].strip()
                        else:
                            clean_content = content.strip()
                        
                        facility_details = json.loads(clean_content)
                        return facility_details
                    except:
                        retries += 1
                        if retries <= max_retries:
                            print(f"  Retrying facility {facility_id} ({retries}/{max_retries})...")
                            time.sleep(DEFAULT_RETRY_DELAY)
                        continue
            else:
                log_error(f"No choices in response for facility {facility_id}")
                retries += 1
                if retries <= max_retries:
                    print(f"  Retrying facility {facility_id} ({retries}/{max_retries})...")
                    time.sleep(DEFAULT_RETRY_DELAY)
                continue
        
        except Exception as e:
            log_error(f"Error getting facility details for {facility_id}: {str(e)}")
            retries += 1
            if retries <= max_retries:
                print(f"  Retrying facility {facility_id} ({retries}/{max_retries})...")
                time.sleep(DEFAULT_RETRY_DELAY)
            continue
    
    # If we've exhausted all retries, return a basic structure
    return {
        "size_sqft": "Unknown",
        "year_built": "Unknown",
        "ownership": "Unknown", 
        "nearby_assets": [],
        "features": [],
        "economic_impact": "Unknown",
        "workforce": "Unknown",
        "facility_code": facility_code if facility_code else "Unknown"
    } 

def enrich_amazon_data(amazon_data, start_index=0, end_index=None, save_interval=20):
    """
    Enrich Amazon fulfillment center data with details from OpenAI in batches
    
    Args:
        amazon_data: Original Amazon data
        start_index: Index to start processing from (for resuming)
        end_index: Index to end processing at (None for all)
        save_interval: Save progress after this many facilities
    """
    if not amazon_data or "fulfillment_centers" not in amazon_data:
        log_error("No valid Amazon data to enrich")
        return None
    
    # Check for existing enriched data to merge with
    existing_enriched = load_existing_enriched_data()
    if existing_enriched:
        print(f"Found existing enriched data with {len(existing_enriched.get('fulfillment_centers', []))} facilities")
        
        # Create a mapping of existing enriched facilities by ID
        enriched_map = {
            center.get('id'): center
            for center in existing_enriched.get('fulfillment_centers', [])
            if center.get('id')
        }
        
        print(f"Mapped {len(enriched_map)} facilities by ID")
        
        # Start with existing enriched data if available
        enriched_data = existing_enriched
    else:
        enriched_map = {}
        # Create a new enriched data structure
        enriched_data = {
            "fulfillment_centers": [],
            "metadata": amazon_data.get("metadata", {})
        }
    
    # Update metadata
    enriched_data["metadata"]["enriched_date"] = datetime.now().strftime("%Y-%m-%d")
    enriched_data["metadata"]["enrichment_source"] = "OpenAI API"
    enriched_data["metadata"]["enrichment_version"] = "2.0"
    
    # Process each fulfillment center
    centers = amazon_data["fulfillment_centers"]
    
    # Determine range to process
    total = len(centers)
    if end_index is None:
        end_index = total
    
    process_centers = centers[start_index:end_index]
    process_total = len(process_centers)
    
    print(f"Processing {process_total} facilities out of {total} total (from index {start_index} to {end_index-1 if end_index else total-1})")
    
    # Prepare a new list for processed centers
    new_centers = []
    
    # Process in batches
    enriched_count = 0
    skipped_count = 0
    error_count = 0
    progress_count = start_index
    
    for batch_start in range(0, process_total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, process_total)
        batch = process_centers[batch_start:batch_end]
        
        print(f"\nProcessing batch {batch_start//BATCH_SIZE + 1} ({batch_start}-{batch_end-1})...")
        
        for i, center in enumerate(batch):
            overall_index = start_index + batch_start + i
            progress_count = overall_index
            center_id = center.get('id', f"Unknown-{overall_index}")
            
            print(f"Processing facility {overall_index+1}/{total}: {center_id} in {center.get('city', 'Unknown')}")
            
            # Check if we already have enriched data for this facility with real content
            if center_id in enriched_map and enriched_map[center_id].get('details'):
                details = enriched_map[center_id].get('details', {})
                
                # Check if there's meaningful data
                has_data = False
                for field in ['size_sqft', 'year_built', 'ownership', 'workforce', 'economic_impact']:
                    if field in details and details[field] != "Unknown":
                        has_data = True
                        break
                
                for field in ['nearby_assets', 'features']:
                    if field in details and isinstance(details[field], list) and len(details[field]) > 0:
                        has_data = True
                        break
                
                if has_data:
                    print(f"  Using existing enriched data for {center_id}")
                    new_centers.append(enriched_map[center_id])
                    skipped_count += 1
                    continue
            
            # Get facility details
            facility_details = get_facility_details(center)
            
            if facility_details:
                # Merge original data with enriched details
                enriched_center = center.copy()
                enriched_center["details"] = facility_details
                new_centers.append(enriched_center)
                
                # Check if we got meaningful data
                has_data = False
                for field in ['size_sqft', 'year_built', 'ownership', 'workforce', 'economic_impact']:
                    if field in facility_details and facility_details[field] != "Unknown":
                        has_data = True
                        break
                
                for field in ['nearby_assets', 'features']:
                    if field in facility_details and isinstance(facility_details[field], list) and len(facility_details[field]) > 0:
                        has_data = True
                        break
                
                if has_data:
                    enriched_count += 1
                    print(f"  ✓ Successfully enriched with meaningful data")
                else:
                    print(f"  ✓ Added to dataset but no meaningful data found")
            else:
                # If failed to get details, just use the original data
                error_count += 1
                print(f"  ✗ Failed to get enriched data")
                enriched_center = center.copy()
                enriched_center["details"] = {
                    "size_sqft": "Unknown",
                    "year_built": "Unknown",
                    "ownership": "Unknown", 
                    "nearby_assets": [],
                    "features": [],
                    "economic_impact": "Unknown",
                    "workforce": "Unknown",
                    "facility_code": "Unknown"
                }
                new_centers.append(enriched_center)
            
            # Wait a bit to avoid API rate limits
            if i < len(batch) - 1:
                time.sleep(FACILITY_DELAY)
            
            # Save progress at intervals
            if (overall_index + 1) % save_interval == 0:
                # Update the centers list
                temp_data = enriched_data.copy()
                temp_data["fulfillment_centers"] = new_centers
                save_progress(temp_data, overall_index + 1)
        
        # Save after each batch
        temp_data = enriched_data.copy()
        temp_data["fulfillment_centers"] = new_centers
        save_progress(temp_data, progress_count + 1)
        
        # Wait between batches
        if batch_end < process_total:
            print(f"Waiting {BATCH_DELAY} seconds before next batch...")
            time.sleep(BATCH_DELAY)
    
    # Update with the new centers
    enriched_data["fulfillment_centers"] = new_centers
    
    # Save the final enriched data
    save_enriched_data(enriched_data)
    
    # Print summary
    print("\nEnrichment process complete!")
    print(f"Total facilities processed: {progress_count - start_index + 1}")
    print(f"Facilities with meaningful data: {enriched_count}")
    print(f"Facilities with no meaningful data: {error_count}")
    print(f"Facilities skipped (already enriched): {skipped_count}")
    
    return enriched_data

def test_script_functionality():
    """Test basic script functionality without running the full enrichment"""
    print("=== TESTING SCRIPT FUNCTIONALITY ===")
    
    # Test file access
    print("\nTesting file access...")
    try:
        if os.path.exists(AMAZ_JSON_PATH):
            print(f"✓ Found original data file: {AMAZ_JSON_PATH}")
        else:
            print(f"✗ Original data file not found: {AMAZ_JSON_PATH}")
        
        if os.path.exists(ENRICHED_JSON_PATH):
            print(f"✓ Found enriched data file: {ENRICHED_JSON_PATH}")
        else:
            print(f"? Enriched data file not found (will be created): {ENRICHED_JSON_PATH}")
            
        # Test loading the original data
        amazon_data = load_amazon_data()
        if amazon_data and "fulfillment_centers" in amazon_data:
            total = len(amazon_data["fulfillment_centers"])
            print(f"✓ Successfully loaded original data with {total} facilities")
            
            # Test with a single sample
            if total > 0:
                sample = amazon_data["fulfillment_centers"][0]
                print(f"\nSample facility: {sample.get('id')} in {sample.get('city')}, {sample.get('state')}")
        else:
            print("✗ Failed to load original data or no facilities found")
    except Exception as e:
        print(f"✗ Error testing file access: {str(e)}")
    
    # Test API access
    print("\nTesting OpenAI API access...")
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Please respond with the text 'API Test Successful'"}
            ],
            "max_tokens": 20
        }
        
        print("Sending test request to OpenAI API...")
        response = requests.post(OPENAI_API_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            response_data = response.json()
            if "choices" in response_data and response_data["choices"]:
                content = response_data["choices"][0]["message"]["content"]
                print(f"✓ API test successful: {content}")
            else:
                print(f"✗ API returned unexpected format: {response_data}")
        else:
            print(f"✗ API test failed with status code {response.status_code}: {response.text}")
    except Exception as e:
        print(f"✗ Error testing API access: {str(e)}")
    
    print("\n=== TEST COMPLETE ===")

def main():
    """Main function with improved user interface"""
    print("=== Amazon Fulfillment Center Data Enrichment Tool (Improved) ===")
    
    # Add test option
    print("\nOptions:")
    print("1. Run enrichment")
    print("2. Test script functionality")
    
    main_choice = input("Enter your choice (1-2): ").strip()
    
    if main_choice == "2":
        test_script_functionality()
        return
    
    # Load existing Amazon data
    amazon_data = load_amazon_data()
    
    if not amazon_data:
        print("Failed to load Amazon data. Exiting.")
        return
    
    # Check for existing enriched data
    existing_data = load_existing_enriched_data()
    if existing_data:
        existing_count = len(existing_data.get('fulfillment_centers', []))
        print(f"Found existing enriched data with {existing_count} facilities")
    
    total_facilities = len(amazon_data.get('fulfillment_centers', []))
    print(f"Loaded {total_facilities} Amazon facilities from original data")
    
    try:
        # Get processing parameters
        print("\nEnrichment options:")
        print("1. Process all facilities")
        print("2. Process a specific range of facilities")
        print("3. Process facilities that don't have meaningful data yet")
        
        choice = input("Enter your choice (1-3): ").strip()
        
        start_index = 0
        end_index = None
        
        if choice == "2":
            start_str = input("Enter starting index (0 to start from beginning): ").strip()
            start_index = int(start_str) if start_str else 0
            
            end_str = input(f"Enter ending index (or Enter for all {total_facilities} facilities): ").strip()
            end_index = int(end_str) if end_str else total_facilities
            
            # Validate range
            if start_index < 0:
                start_index = 0
            if end_index > total_facilities:
                end_index = total_facilities
                
        elif choice == "3":
            # Process facilities without meaningful data
            print("Will process only facilities without enriched data")
            start_index = 0
            end_index = total_facilities
        
        # Ask for save interval
        save_interval_str = input("Enter progress save interval (default: 10 facilities): ").strip()
        save_interval = int(save_interval_str) if save_interval_str else 10
        
        # Configure batch settings
        batch_size_str = input(f"Enter batch size (default: {BATCH_SIZE}): ").strip()
        batch_size = int(batch_size_str) if batch_size_str else BATCH_SIZE
        
        batch_delay_str = input(f"Enter seconds between batches (default: {BATCH_DELAY}): ").strip()
        batch_delay = int(batch_delay_str) if batch_delay_str else BATCH_DELAY
        
        facility_delay_str = input(f"Enter seconds between facilities (default: {FACILITY_DELAY}): ").strip()
        facility_delay = int(facility_delay_str) if facility_delay_str else FACILITY_DELAY
        
        # Update global settings
        global BATCH_SIZE, BATCH_DELAY, FACILITY_DELAY
        BATCH_SIZE = batch_size
        BATCH_DELAY = batch_delay
        FACILITY_DELAY = facility_delay
        
        # Confirm parameters
        print("\nEnrichment parameters:")
        print(f"- Starting index: {start_index}")
        print(f"- Ending index: {end_index if end_index is not None else total_facilities} (of {total_facilities} total)")
        print(f"- Batch size: {BATCH_SIZE} facilities")
        print(f"- Batch delay: {BATCH_DELAY} seconds")
        print(f"- Facility delay: {FACILITY_DELAY} seconds")
        print(f"- Save interval: Every {save_interval} facilities")
        
        confirm = input("\nStart enrichment process? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Enrichment cancelled. Exiting.")
            return
        
        print("\nStarting enrichment process...")
        
        # Start enrichment
        enriched_data = enrich_amazon_data(
            amazon_data, 
            start_index=start_index,
            end_index=end_index,
            save_interval=save_interval
        )
        
        if enriched_data:
            print("Enrichment completed successfully!")
        else:
            print("Enrichment failed or was cancelled.")
    
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
    except Exception as e:
        log_error(f"An error occurred: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 