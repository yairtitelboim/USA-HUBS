#!/usr/bin/env python3
import os
import json
import time
import requests
import PyPDF2
import re

# Configuration
PDF_FILE = "county-viz-app/public/data/final/Hubs/US_Fulfillment_Center_100.pdf"
OUTPUT_JSON = "county-viz-app/public/data/final/Hubs/AMAZ.json"
API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')  # Google Places API key

def extract_addresses_from_pdf(pdf_path):
    """Extract addresses from the PDF file."""
    print(f"Extracting addresses from {pdf_path}...")
    addresses = []
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extract text from each page
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                # Process the text to extract addresses
                # This pattern may need to be adjusted based on the actual PDF format
                # For now, we'll assume each line that has a state abbreviation is an address
                lines = text.split('\n')
                
                for line in lines:
                    # Look for lines that likely contain addresses (has state abbreviation)
                    # This regex looks for a pattern like "City, ST ZIP" or similar
                    if re.search(r'[A-Z]{2}\s+\d{5}', line) or re.search(r'[A-Z]{2}[\s,-]+\d{5}', line):
                        # Clean up the address
                        address = line.strip()
                        if address and len(address) > 10:  # Basic validation to avoid fragments
                            addresses.append(address)
    
    except Exception as e:
        print(f"Error extracting addresses: {str(e)}")
    
    print(f"Found {len(addresses)} potential addresses")
    return addresses

def geocode_address(address):
    """Convert address to lat/long using Google Geocoding API."""
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": API_KEY
    }
    
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if data["status"] == "OK":
            location = data["results"][0]["geometry"]["location"]
            formatted_address = data["results"][0]["formatted_address"]
            
            # Extract city and state if available
            city = ""
            state = ""
            state_code = ""
            
            for component in data["results"][0]["address_components"]:
                if "locality" in component["types"]:
                    city = component["long_name"]
                if "administrative_area_level_1" in component["types"]:
                    state = component["long_name"]
                    state_code = component["short_name"]
            
            return {
                "original_address": address,
                "formatted_address": formatted_address,
                "city": city,
                "state": state,
                "state_code": state_code,
                "lat": location["lat"],
                "lng": location["lng"]
            }
        else:
            print(f"Geocoding error for address '{address}': {data['status']}")
            return None
    
    except Exception as e:
        print(f"Error geocoding address '{address}': {str(e)}")
        return None

def main():
    # Extract addresses from PDF
    addresses = extract_addresses_from_pdf(PDF_FILE)
    
    # Geocode each address
    fulfillment_centers = []
    
    for i, address in enumerate(addresses):
        print(f"Geocoding address {i+1}/{len(addresses)}: {address}")
        
        geocoded = geocode_address(address)
        if geocoded:
            # Add additional metadata
            geocoded["id"] = f"AMAZ-{i+1:03d}"
            geocoded["type"] = "Fulfillment Center"
            geocoded["company"] = "Amazon"
            fulfillment_centers.append(geocoded)
        
        # Sleep to avoid hitting API rate limits
        if i < len(addresses) - 1:
            time.sleep(0.2)
    
    # Save to JSON file
    output_data = {
        "fulfillment_centers": fulfillment_centers,
        "metadata": {
            "count": len(fulfillment_centers),
            "source": "US_Fulfillment_Center_100.pdf",
            "date_extracted": time.strftime("%Y-%m-%d"),
            "geocoded_with": "Google Maps Geocoding API"
        }
    }
    
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Successfully geocoded {len(fulfillment_centers)} addresses")
    print(f"JSON data saved to {OUTPUT_JSON}")

if __name__ == "__main__":
    main() 