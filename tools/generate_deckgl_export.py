#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Generate high-resolution exports from Deck.gl prototype.

This script uses Selenium and Chrome to open the Deck.gl prototype
and generate high-resolution PNG exports.
"""

import os
import time
import argparse
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def generate_export(html_path, output_dir, width=3840, height=2160, wait_time=5):
    """
    Generate a high-resolution PNG export from a Deck.gl prototype.
    
    Args:
        html_path: Path to the HTML file
        output_dir: Directory to save the PNG export
        width: Width of the browser window (default: 3840 for 4K)
        height: Height of the browser window (default: 2160 for 4K)
        wait_time: Time to wait for the map to load (in seconds)
        
    Returns:
        Path to the saved PNG file
    """
    print(f"Generating export from {html_path}...")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    chrome_options.add_argument(f"--window-size={width},{height}")  # Set window size
    chrome_options.add_argument("--hide-scrollbars")  # Hide scrollbars
    
    # Create a new Chrome driver
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(html_path)
        file_url = f"file://{abs_path}"
        
        # Open the HTML file
        driver.get(file_url)
        
        # Wait for the map to load
        print(f"Waiting {wait_time} seconds for the map to load...")
        time.sleep(wait_time)
        
        # Generate file name
        file_name = f"deckgl_export_{width}x{height}.png"
        output_path = os.path.join(output_dir, file_name)
        
        # Take a screenshot
        driver.save_screenshot(output_path)
        print(f"Screenshot saved to: {output_path}")
        
        # Try to use the export button if available
        try:
            # Wait for the export button to be clickable
            export_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "screenshot-button"))
            )
            
            # Click the export button
            export_button.click()
            
            # Wait for the download to complete
            print("Clicked export button. Note: The browser's built-in export may be saved to your downloads folder.")
            time.sleep(2)
        except Exception as e:
            print(f"Warning: Could not use the export button: {str(e)}")
        
        return output_path
    
    finally:
        # Close the browser
        driver.quit()


def main():
    """Main function to generate exports from Deck.gl prototype."""
    parser = argparse.ArgumentParser(description="Generate high-resolution exports from Deck.gl prototype")
    
    # Required arguments
    parser.add_argument("--html", required=True,
                        help="Path to the HTML file")
    
    # Optional arguments
    parser.add_argument("--output-dir", default="qa/exports",
                        help="Directory to save the PNG export (default: qa/exports)")
    parser.add_argument("--width", type=int, default=3840,
                        help="Width of the browser window (default: 3840 for 4K)")
    parser.add_argument("--height", type=int, default=2160,
                        help="Height of the browser window (default: 2160 for 4K)")
    parser.add_argument("--wait-time", type=int, default=5,
                        help="Time to wait for the map to load (in seconds)")
    
    args = parser.parse_args()
    
    # Generate export
    output_path = generate_export(
        args.html,
        args.output_dir,
        args.width,
        args.height,
        args.wait_time
    )
    
    print(f"Export generated successfully: {output_path}")


if __name__ == "__main__":
    main()
