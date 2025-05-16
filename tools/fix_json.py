#!/usr/bin/env python3
"""
Fix corrupted JSON file by identifying and repairing the issue.
"""

import json
import os
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/fix_json.log')
    ]
)
logger = logging.getLogger(__name__)

def fix_json_file(input_file, output_file):
    """
    Fix a corrupted JSON file.
    
    Args:
        input_file: Path to the corrupted JSON file
        output_file: Path to save the fixed JSON file
    
    Returns:
        True if the file was fixed successfully, False otherwise
    """
    logger.info(f"Attempting to fix JSON file: {input_file}")
    
    try:
        # First, try to load the file to see if it's actually corrupted
        with open(input_file, 'r') as f:
            try:
                data = json.load(f)
                logger.info("JSON file is valid, no fix needed")
                return True
            except json.JSONDecodeError as e:
                logger.error(f"JSON file is corrupted: {e}")
                # Continue with the fix
    
        # Read the file as text
        with open(input_file, 'r') as f:
            content = f.read()
        
        # Try to identify where the issue is
        error_line = None
        error_char = None
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            error_line = e.lineno
            error_char = e.colno
            error_pos = e.pos
            logger.info(f"Error at line {error_line}, column {error_char}, position {error_pos}")
        
        if error_line is None:
            logger.error("Could not identify the error location")
            return False
        
        # Split the content into lines
        lines = content.split('\n')
        
        # Check if we're near the end of the file
        if error_line >= len(lines) - 5:
            logger.info("Error is near the end of the file, attempting to fix by completing the JSON structure")
            
            # Try to find the last valid feature
            try:
                # Find the last complete feature by looking for "}," pattern
                last_feature_end = content.rindex("},", 0, error_pos)
                
                # Create a new content with everything up to the last valid feature
                new_content = content[:last_feature_end+1] + "\n    ]\n}"
                
                # Try to parse the new content
                json.loads(new_content)
                
                # If we get here, the fix worked
                logger.info("Successfully fixed the JSON file by completing the structure")
                
                # Write the fixed content to the output file
                with open(output_file, 'w') as f:
                    f.write(new_content)
                
                return True
            except Exception as e:
                logger.error(f"Error fixing JSON file: {e}")
                return False
        else:
            # The error is somewhere in the middle of the file
            logger.info("Error is in the middle of the file, attempting to fix by parsing features individually")
            
            try:
                # Read the file and extract the features
                with open(input_file, 'r') as f:
                    # Read the first part of the file to get the header
                    header = ""
                    for i in range(10):  # Assuming the header is within the first 10 lines
                        line = f.readline()
                        header += line
                        if '"features": [' in line:
                            break
                
                # Find where the features array starts
                features_start = header.index('"features": [') + len('"features": [')
                
                # Create a new content with the header
                new_content = header[:features_start]
                
                # Now read the rest of the file and extract valid features
                with open(input_file, 'r') as f:
                    # Skip the header
                    f.seek(features_start)
                    
                    # Read the rest of the file
                    rest = f.read()
                    
                    # Split by feature delimiter
                    features = rest.split('},')
                    
                    # Process each feature
                    valid_features = []
                    for i, feature in enumerate(features[:-1]):  # Skip the last one which might be incomplete
                        try:
                            # Add the closing brace back
                            feature_json = feature + '}'
                            
                            # Try to parse it
                            json.loads(feature_json)
                            
                            # If we get here, it's valid
                            valid_features.append(feature)
                        except Exception as e:
                            logger.warning(f"Feature {i} is invalid: {e}")
                    
                    # Combine the valid features
                    new_content += ','.join(valid_features)
                    if valid_features:
                        new_content += '}'  # Add the closing brace for the last feature
                    
                    # Close the features array and the root object
                    new_content += "\n    ]\n}"
                    
                    # Try to parse the new content
                    json.loads(new_content)
                    
                    # If we get here, the fix worked
                    logger.info(f"Successfully fixed the JSON file with {len(valid_features)} valid features")
                    
                    # Write the fixed content to the output file
                    with open(output_file, 'w') as f:
                        f.write(new_content)
                    
                    return True
            except Exception as e:
                logger.error(f"Error fixing JSON file: {e}")
                return False
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def main():
    """Main function to fix a corrupted JSON file."""
    if len(sys.argv) < 2:
        print("Usage: python fix_json.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file + ".fixed"
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    if fix_json_file(input_file, output_file):
        logger.info(f"Successfully fixed JSON file: {output_file}")
        sys.exit(0)
    else:
        logger.error(f"Failed to fix JSON file: {input_file}")
        sys.exit(1)

if __name__ == "__main__":
    main()
