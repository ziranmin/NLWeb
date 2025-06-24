"""
Example usage of the DoorDash restaurant scraper.

This file demonstrates how to use the scraper functions to extract
Schema.org markup from DoorDash restaurant pages.
"""

from dd_scrape import (
    scrape_doordash_restaurant,
    scrape_doordash_restaurant_enhanced,
    scrape_multiple_restaurants
)


def example_single_restaurant():
    """Example: Scrape a single restaurant."""
    url = "https://www.doordash.com/store/love-art-sushi-downtown-crossing-boston-1543727"
    
    print("=== Single Restaurant Scraping ===")
    result = scrape_doordash_restaurant_enhanced(url, output_dir="scraped_data")
    
    if result:
        print(f"Success! Data saved to: {result}")
    else:
        print("Failed to scrape restaurant data")


def example_multiple_restaurants():
    """Example: Scrape multiple restaurants."""
    urls = [
        "https://www.doordash.com/store/restaurant-1",
        "https://www.doordash.com/store/restaurant-2",
        # Add more URLs as needed
    ]
    
    print("\n=== Multiple Restaurants Scraping ===")
    results = scrape_multiple_restaurants(urls, output_dir="scraped_data", delay=3.0)
    
    print(f"Successfully scraped {len(results)} restaurants")
    for result in results:
        print(f"  - {result}")


def example_custom_settings():
    """Example: Use enhanced scraper with custom settings."""
    url = "https://www.doordash.com/store/your-restaurant-url"
    
    print("\n=== Enhanced Scraper with Custom Settings ===")
    result = scrape_doordash_restaurant_enhanced(
        url=url,
        output_dir="custom_output",
        use_session=True,
        retry_attempts=5
    )
    
    if result:
        print(f"Success with enhanced settings! Data saved to: {result}")
    else:
        print("Failed even with enhanced settings")


if __name__ == "__main__":
    print("DoorDash Scraper Examples")
    print("=" * 40)
    
    # Run examples
    example_single_restaurant()
    # example_multiple_restaurants()  # Uncomment to try multiple restaurants
    # example_custom_settings()        # Uncomment to try custom settings
    
    print("\n" + "=" * 40)
    print("Note: DoorDash has anti-bot measures, so scraping may not always work.")
    print("The enhanced scraper has better success rates with retry logic and")
    print("randomized headers, but success is not guaranteed.")
