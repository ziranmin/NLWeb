# import requests
# from bs4 import BeautifulSoup
# import json
# import re
# import os
# from urllib.parse import urlparse
# import time
# from typing import Optional
# import random


# def get_headers():
#     """
#     Returns randomized headers to avoid detection.
#     """
#     user_agents = [
#         'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
#         'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
#         'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
#         'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
#     ]
    
#     return {
#         'User-Agent': random.choice(user_agents),
#         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
#         'Accept-Language': 'en-US,en;q=0.5',
#         'Accept-Encoding': 'gzip, deflate, br',
#         'DNT': '1',
#         'Connection': 'keep-alive',
#         'Upgrade-Insecure-Requests': '1',
#         'Sec-Fetch-Dest': 'document',
#         'Sec-Fetch-Mode': 'navigate',
#         'Sec-Fetch-Site': 'none',
#         'Cache-Control': 'max-age=0'
#     }


# def scrape_doordash_restaurant_enhanced(url: str,
#                                        output_dir: str = "scraped_data",
#                                        use_session: bool = True,
#                                        retry_attempts: int = 3
#                                        ) -> Optional[str]:
#     """
#     Enhanced scraper with session management and retry logic.
    
#     Args:
#         url (str): The DoorDash restaurant URL
#         output_dir (str): Directory to save the JSON file
#         use_session (bool): Whether to use a session for requests
#         retry_attempts (int): Number of retry attempts
        
#     Returns:
#         str: Path to the saved JSON file, or None if scraping failed
#     """
    
#     # Create output directory if it doesn't exist
#     os.makedirs(output_dir, exist_ok=True)
    
#     # Create session if requested
#     if use_session:
#         session = requests.Session()
#         session.headers.update(get_headers())
#     else:
#         session = requests
    
#     for attempt in range(retry_attempts):
#         try:
#             print(f"Fetching page: {url} (Attempt {attempt + 1}/{retry_attempts})")
            
#             # Add random delay between attempts
#             if attempt > 0:
#                 delay = random.uniform(3, 7)
#                 print(f"Waiting {delay:.1f} seconds before retry...")
#                 time.sleep(delay)
            
#             # Update headers for each attempt
#             if use_session:
#                 session.headers.update(get_headers())
#             else:
#                 headers = get_headers()
            
#             # Make the request
#             if use_session:
#                 response = session.get(url, timeout=30)
#             else:
#                 response = requests.get(url, headers=headers, timeout=30)
            
#             response.raise_for_status()
            
#             # Parse the HTML
#             soup = BeautifulSoup(response.content, 'html.parser')
            
#             # Find all script tags with type="application/ld+json"
#             schema_scripts = soup.find_all('script', 
#                                          {'type': 'application/ld+json'})
            
#             if not schema_scripts:
#                 print("No Schema.org markup found on the page")
#                 return None
            
#             print(f"Found {len(schema_scripts)} Schema.org script(s)")
            
#             # Process each schema script
#             restaurant_data = None
#             for i, script in enumerate(schema_scripts):
#                 try:
#                     # Parse the JSON content
#                     if script.string:
#                         json_content = script.string.strip()
#                         schema_data = json.loads(json_content)
                        
#                         # Check if this is restaurant data
#                         is_restaurant = (isinstance(schema_data, dict) and 
#                                        schema_data.get('@type') == 'Restaurant')
#                         if is_restaurant:
#                             restaurant_data = schema_data
#                             print(f"Found Restaurant schema in script {i+1}")
#                             break
#                         elif isinstance(schema_data, list):
#                             # Sometimes the data is in a list
#                             for item in schema_data:
#                                 is_restaurant_item = (isinstance(item, dict) and 
#                                                     item.get('@type') == 'Restaurant')
#                                 if is_restaurant_item:
#                                     restaurant_data = item
#                                     print(f"Found Restaurant schema in script {i+1} (list format)")
#                                     break
#                             if restaurant_data:
#                                 break
                                
#                 except json.JSONDecodeError as e:
#                     print(f"Error parsing JSON in script {i+1}: {e}")
#                     continue
            
#             if not restaurant_data:
#                 print("No Restaurant schema found in any of the scripts")
#                 return None
            
#             # Generate filename from URL
#             parsed_url = urlparse(url)
#             path_parts = parsed_url.path.strip('/').split('/')
#             if path_parts:
#                 # Use the last part of the path as filename base
#                 filename_base = path_parts[-1]
#                 # Clean the filename
#                 filename_base = re.sub(r'[^\w\-_]', '_', filename_base)
#             else:
#                 filename_base = "doordash_restaurant"
            
#             # Create unique filename
#             timestamp = int(time.time())
#             filename = f"{filename_base}_{timestamp}.json"
#             filepath = os.path.join(output_dir, filename)
            
#             # Save the data
#             with open(filepath, 'w', encoding='utf-8') as f:
#                 json.dump(restaurant_data, f, indent=2, ensure_ascii=False)
            
#             print(f"Schema.org data saved to: {filepath}")
            
#             # Print summary information
#             restaurant_name = restaurant_data.get('name', 'Unknown')
#             address = restaurant_data.get('address', {})
#             street = (address.get('streetAddress', '') 
#                      if isinstance(address, dict) else '')
#             city = (address.get('addressLocality', '') 
#                    if isinstance(address, dict) else '')
            
#             print(f"Restaurant: {restaurant_name}")
#             if street or city:
#                 print(f"Address: {street}, {city}")
            
#             # Check for menu data
#             menu_data = restaurant_data.get('hasMenu', {})
#             if menu_data:
#                 menu_sections = menu_data.get('hasMenuSection', [])
#                 if isinstance(menu_sections, list) and len(menu_sections) > 0:
#                     # Handle nested list structure
#                     if isinstance(menu_sections[0], list):
#                         menu_sections = menu_sections[0]
#                     print(f"Found {len(menu_sections)} menu sections")
            
#             return filepath
            
#         except requests.RequestException as e:
#             print(f"Error fetching the page (attempt {attempt + 1}): {e}")
#             if attempt == retry_attempts - 1:
#                 print("All retry attempts failed")
#                 return None
#             continue
#         except Exception as e:
#             print(f"Unexpected error: {e}")
#             return None
    
#     return None


# def scrape_multiple_restaurants(urls: list, output_dir: str = "scraped_data", delay: float = 2.0) -> list:
#     """
#     Scrapes multiple DoorDash restaurant pages.
    
#     Args:
#         urls (list): List of DoorDash restaurant URLs
#         output_dir (str): Directory to save the JSON files
#         delay (float): Delay between requests in seconds
        
#     Returns:
#         list: List of successfully saved file paths
#     """
#     successful_files = []
    
#     for i, url in enumerate(urls):
#         print(f"\n--- Processing {i+1}/{len(urls)} ---")
        
#         filepath = scrape_doordash_restaurant_enhanced(url, output_dir)
#         if filepath:
#             successful_files.append(filepath)
        
#         # Add delay between requests to be respectful
#         if i < len(urls) - 1:  # Don't delay after the last request
#             print(f"Waiting {delay} seconds before next request...")
#             time.sleep(delay)
    
#     print(f"\n--- Summary ---")
#     print(f"Successfully scraped {len(successful_files)}/{len(urls)} restaurants")
    
#     return successful_files


# def main():
#     """
#     Example usage of the scraper functions.
#     """
#     # Example URL
#     example_url = "https://www.doordash.com/store/love-art-sushi-downtown-crossing-boston-1543727"
    
#     print("DoorDash Restaurant Scraper")
#     print("=" * 40)    # Try the enhanced scraper
#     result = scrape_doordash_restaurant_enhanced(example_url)
    
#     if result:
#         print("\nScraping completed successfully!")
#         print(f"Output file: {result}")
#     else:
#         print("\nScraping failed!")
#         print("\nNote: DoorDash may be blocking automated requests.")
#         print("Try using the function manually with different URLs or")
#         print("consider using alternative data sources.")


# if __name__ == "__main__":
#     main()


import requests
from bs4 import BeautifulSoup

def extract_ld_json(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        ld_json_scripts = soup.find_all('script', type='application/ld+json')
        return [script.string for script in ld_json_scripts if script.string]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return []

# Example usage:
ld_json_data = extract_ld_json("https://www.doordash.com/store/love-art-sushi-downtown-crossing-boston-1543727")
for i, data in enumerate(ld_json_data, 1):
    print(f"LD+JSON Block {i}:\n{data}\n")
