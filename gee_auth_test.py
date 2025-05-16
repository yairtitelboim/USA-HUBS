#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GEE Service Account Authentication Test

This script tests authentication with GEE using service account.
"""

import os
import json
import ee

# Print Python and package versions for debugging
print(f"Python version: {os.sys.version}")
print(f"EE API version: {ee.__version__}")

# Path to the service account JSON file
service_account_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "config/gee/gentle-cinema-458613-f3-51d8ea2711e7.json"
)

# Print service account details (without private key)
with open(service_account_path, 'r') as f:
    service_account = json.load(f)
    # Remove private key for security
    if 'private_key' in service_account:
        service_account['private_key'] = '[REDACTED]'
    print(f"Service account details: {json.dumps(service_account, indent=2)}")

# Set the environment variable for authentication
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_account_path
print(f"Using service account: {service_account_path}")

# Try to authenticate with Earth Engine
try:
    # Try with default credentials and project ID
    print("Attempting to initialize with default credentials and project ID...")
    ee.Initialize(project=service_account['project_id'])
    print("Earth Engine initialized successfully with default credentials and project ID!")
    # Try a simple API call
    try:
        print("Testing API with a simple call...")
        image = ee.Image('USGS/SRTMGL1_003')
        print("Successfully created an ee.Image object!")
        info = image.getInfo()
        print("Successfully retrieved image info!")
    except Exception as e:
        print(f"Error making API call: {e}")
except Exception as e:
    print(f"Error initializing with default credentials: {e}")

    try:
        # Try with service account credentials and explicit project
        print("\nAttempting to initialize with explicit service account credentials and project ID...")
        credentials = ee.ServiceAccountCredentials(
            email=service_account['client_email'],
            key_file=service_account_path
        )
        ee.Initialize(credentials, project=service_account['project_id'])
        print("Earth Engine initialized successfully with explicit service account credentials and project ID!")
        # Try a simple API call
        try:
            print("Testing API with a simple call...")
            image = ee.Image('USGS/SRTMGL1_003')
            print("Successfully created an ee.Image object!")
            info = image.getInfo()
            print("Successfully retrieved image info!")
        except Exception as e:
            print(f"Error making API call: {e}")
    except Exception as e:
        print(f"Error initializing with explicit service account credentials: {e}")

        try:
            # Try with interactive authentication and project ID
            print("\nAttempting to initialize with interactive authentication and project ID...")
            ee.Authenticate()
            ee.Initialize(project=service_account['project_id'])
            print("Earth Engine initialized successfully with interactive authentication and project ID!")
            # Try a simple API call
            try:
                print("Testing API with a simple call...")
                image = ee.Image('USGS/SRTMGL1_003')
                print("Successfully created an ee.Image object!")
                info = image.getInfo()
                print("Successfully retrieved image info!")
            except Exception as e:
                print(f"Error making API call: {e}")
        except Exception as e:
            print(f"Error initializing with interactive authentication: {e}")
            print("\nAll authentication methods failed. Please check your Earth Engine account and service account setup.")
