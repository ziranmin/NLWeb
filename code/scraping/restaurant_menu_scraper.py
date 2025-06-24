#!/usr/bin/env python3
"""
Restaurant menu scraper that extracts individual menu items and outputs structured data.
This script can output RSS or JSONL formats for NLWeb's vectorisation.

Usage:
    python restaurant_menu_scraper.py https://restaurant-website.com --format nlweb
    python restaurant_menu_scraper.py https://restaurant-website.com --format rss
"""

import sys
import json
import uuid
import argparse
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlparse, urljoin
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass, asdict
import re
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MenuItem:
    """Data class for a menu item"""
    name: str
    description: str = ""
    price: str = ""
    category: str = ""
    dietary_info: List[str] = None
    allergens: List[str] = None
    image_url: str = ""
    availability: str = ""
    restaurant_name: str = ""
    restaurant_url: str = ""
    scraped_at: str = ""
    
    def __post_init__(self):
        if self.dietary_info is None:
            self.dietary_info = []
        if self.allergens is None:
            self.allergens = []
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()

class RestaurantMenuScraper:
    """Scraper for extracting individual menu items from restaurant websites"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.menu_items: List[MenuItem] = []
        
    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from a URL"""
        async with aiohttp.ClientSession() as session:
            for attempt in range(self.max_retries):
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            logger.warning(f"HTTP {response.status} for {url}")
                except Exception as e:
                    logger.warning(f"Error fetching {url} (attempt {attempt + 1}): {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
        return None

    def extract_schema_menu_items(self, html: str, base_url: str) -> List[MenuItem]:
        """Extract menu items from JSON-LD schema markup"""
        items = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find JSON-LD scripts
        json_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                items.extend(self._process_schema_data(data, base_url))
            except json.JSONDecodeError:
                continue
                
        return items
    
    def _process_schema_data(self, data, base_url: str) -> List[MenuItem]:
        """Recursively process schema data to find menu items"""
        items = []
        
        if isinstance(data, dict):
            # Check if this is a Restaurant with a menu
            if data.get('@type') == 'Restaurant':
                restaurant_name = data.get('name', '')
                if 'hasMenu' in data:
                    menu_data = data['hasMenu']
                    items.extend(self._extract_from_menu(menu_data, restaurant_name, base_url))
                elif 'menu' in data:
                    menu_data = data['menu']
                    items.extend(self._extract_from_menu(menu_data, restaurant_name, base_url))
            
            # Check if this is a Menu directly
            elif data.get('@type') == 'Menu':
                items.extend(self._extract_from_menu(data, '', base_url))
            
            # Check if this is a MenuSection
            elif data.get('@type') == 'MenuSection':
                items.extend(self._extract_from_menu_section(data, '', base_url))
            
            # Check if this is a MenuItem directly
            elif data.get('@type') == 'MenuItem':
                item = self._create_menu_item_from_schema(data, '', '', base_url)
                if item:
                    items.append(item)
            
            # Recursively check nested objects
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    items.extend(self._process_schema_data(value, base_url))
        
        elif isinstance(data, list):
            for item in data:
                items.extend(self._process_schema_data(item, base_url))
        
        return items
    
    def _extract_from_menu(self, menu_data, restaurant_name: str, base_url: str) -> List[MenuItem]:
        """Extract items from a Menu schema object"""
        items = []
        
        if isinstance(menu_data, dict):
            # Check for menu sections
            if 'hasMenuSection' in menu_data:
                sections = menu_data['hasMenuSection']
                if not isinstance(sections, list):
                    sections = [sections]
                
                for section in sections:
                    items.extend(self._extract_from_menu_section(section, restaurant_name, base_url))
            
            # Check for direct menu items
            if 'hasMenuItem' in menu_data:
                menu_items = menu_data['hasMenuItem']
                if not isinstance(menu_items, list):
                    menu_items = [menu_items]
                
                for menu_item in menu_items:
                    item = self._create_menu_item_from_schema(menu_item, restaurant_name, '', base_url)
                    if item:
                        items.append(item)
        
        return items
    
    def _extract_from_menu_section(self, section_data, restaurant_name: str, base_url: str) -> List[MenuItem]:
        """Extract items from a MenuSection schema object"""
        items = []
        
        if isinstance(section_data, dict):
            category = section_data.get('name', '')
            
            if 'hasMenuItem' in section_data:
                menu_items = section_data['hasMenuItem']
                if not isinstance(menu_items, list):
                    menu_items = [menu_items]
                
                for menu_item in menu_items:
                    item = self._create_menu_item_from_schema(menu_item, restaurant_name, category, base_url)
                    if item:
                        items.append(item)
        
        return items
    
    def _create_menu_item_from_schema(self, item_data, restaurant_name: str, category: str, base_url: str) -> Optional[MenuItem]:
        """Create a MenuItem from schema data"""
        if not isinstance(item_data, dict):
            return None
        
        name = item_data.get('name', '')
        if not name:
            return None
        
        description = item_data.get('description', '')
        
        # Extract price information
        price = ''
        if 'offers' in item_data:
            offers = item_data['offers']
            if isinstance(offers, list) and offers:
                offers = offers[0]
            if isinstance(offers, dict):
                price = offers.get('price', '') or offers.get('priceSpecification', {}).get('price', '')
                if price and 'priceCurrency' in offers:
                    currency = offers.get('priceCurrency', '$')
                    if not str(price).startswith(currency):
                        price = f"{currency}{price}"
        
        # Extract dietary information
        dietary_info = []
        if 'suitableForDiet' in item_data:
            diet_data = item_data['suitableForDiet']
            if isinstance(diet_data, list):
                dietary_info = diet_data
            else:
                dietary_info = [diet_data]
        
        # Extract allergen information
        allergens = []
        if 'allergens' in item_data:
            allergen_data = item_data['allergens']
            if isinstance(allergen_data, list):
                allergens = allergen_data
            else:
                allergens = [allergen_data]
        
        # Extract image URL
        image_url = ''
        if 'image' in item_data:
            image_data = item_data['image']
            if isinstance(image_data, str):
                image_url = urljoin(base_url, image_data)
            elif isinstance(image_data, dict):
                image_url = urljoin(base_url, image_data.get('url', ''))
        
        return MenuItem(
            name=name,
            description=description,
            price=str(price) if price else '',
            category=category,
            dietary_info=dietary_info,
            allergens=allergens,
            image_url=image_url,
            restaurant_name=restaurant_name,
            restaurant_url=base_url
        )
    
    def extract_html_menu_items(self, html: str, base_url: str) -> List[MenuItem]:
        """Extract menu items from HTML structure (fallback method)"""
        items = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Common selectors for menu items
        menu_selectors = [
            '.menu-item', '.menuitem', '.menu_item',
            '.dish', '.food-item', '.product',
            '[data-menu-item]', '[data-dish]'
        ]
        
        restaurant_name = self._extract_restaurant_name(soup)
        
        for selector in menu_selectors:
            menu_elements = soup.select(selector)
            if menu_elements:
                logger.info(f"Found {len(menu_elements)} menu items with selector: {selector}")
                for element in menu_elements:
                    item = self._create_menu_item_from_html(element, restaurant_name, base_url)
                    if item:
                        items.append(item)
                break  # Use the first selector that finds items
        
        return items
    
    def _extract_restaurant_name(self, soup: BeautifulSoup) -> str:
        """Extract restaurant name from HTML"""
        # Try various common locations for restaurant name
        selectors = [
            'h1', '.restaurant-name', '.site-title', 
            '.brand-name', 'title', '.header-title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text().strip():
                return element.get_text().strip()
        
        return ''
    
    def _create_menu_item_from_html(self, element, restaurant_name: str, base_url: str) -> Optional[MenuItem]:
        """Create a MenuItem from HTML element"""
        # Extract name
        name_selectors = ['.name', '.title', '.dish-name', 'h3', 'h4', '.item-name']
        name = ''
        for selector in name_selectors:
            name_elem = element.select_one(selector)
            if name_elem:
                name = name_elem.get_text().strip()
                break
        
        if not name:
            # Try to get text from the element itself
            name = element.get_text().strip()[:100]  # Limit length
            if not name:
                return None
        
        # Extract description
        desc_selectors = ['.description', '.desc', '.details', '.ingredients', 'p']
        description = ''
        for selector in desc_selectors:
            desc_elem = element.select_one(selector)
            if desc_elem and desc_elem != element.select_one(name_selectors[0] if name_selectors else None):
                description = desc_elem.get_text().strip()
                break
        
        # Extract price
        price_selectors = ['.price', '.cost', '.amount', '[data-price]']
        price = ''
        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text().strip()
                # Extract price using regex
                price_match = re.search(r'[\$£€¥]?[\d,]+\.?\d*', price_text)
                if price_match:
                    price = price_match.group()
                break
        
        # Extract category from parent elements
        category = ''
        parent = element.parent
        while parent and not category:
            category_selectors = ['.category', '.section', '.menu-section', 'h2', 'h3']
            for selector in category_selectors:
                cat_elem = parent.select_one(selector)
                if cat_elem:
                    category = cat_elem.get_text().strip()
                    break
            parent = parent.parent
        
        # Extract image
        image_url = ''
        img_elem = element.select_one('img')
        if img_elem:
            img_src = img_elem.get('src') or img_elem.get('data-src')
            if img_src:
                image_url = urljoin(base_url, img_src)
        
        return MenuItem(
            name=name,
            description=description,
            price=price,
            category=category,
            restaurant_name=restaurant_name,
            restaurant_url=base_url,
            image_url=image_url
        )
    
    async def scrape_menu(self, url: str) -> Tuple[List[MenuItem], Optional[str]]:
        """Main method to scrape menu from a restaurant website"""
        logger.info(f"Scraping menu from: {url}")
        
        html = await self.fetch_page(url)
        if not html:
            logger.error(f"Failed to fetch content from {url}")
            return [], None
        
        # Try schema markup first
        schema_items = self.extract_schema_menu_items(html, url)
        if schema_items:
            logger.info(f"Found {len(schema_items)} menu items from schema markup")
            return schema_items, None
        
        # Fallback to HTML parsing
        logger.info("No schema markup found, trying HTML parsing")
        html_items = self.extract_html_menu_items(html, url)
        if html_items:
            logger.info(f"Found {len(html_items)} menu items from HTML parsing")
            return html_items, None
        
        # No menu items found - treat as regular page
        logger.info("No menu items found, treating as regular page content")
        return [], html

class MenuDataExporter:
    """Export menu data in various formats"""
    
    @staticmethod
    def to_rss(menu_items: List[MenuItem], output_file: str, channel_title: str = "Restaurant Menu"):
        """Export menu items to RSS format"""
        # Create RSS root element
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        
        # Channel metadata
        ET.SubElement(channel, "title").text = channel_title
        ET.SubElement(channel, "description").text = f"Menu items from {channel_title}"
        ET.SubElement(channel, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        if menu_items:
            ET.SubElement(channel, "link").text = menu_items[0].restaurant_url
        
        # Add each menu item as an RSS item
        for menu_item in menu_items:
            item = ET.SubElement(channel, "item")
            
            title = f"{menu_item.name}"
            if menu_item.category:
                title += f" ({menu_item.category})"
            ET.SubElement(item, "title").text = title
            
            # Description includes price and details
            description_parts = []
            if menu_item.price:
                description_parts.append(f"Price: {menu_item.price}")
            if menu_item.description:
                description_parts.append(menu_item.description)
            if menu_item.dietary_info:
                description_parts.append(f"Dietary: {', '.join(menu_item.dietary_info)}")
            
            ET.SubElement(item, "description").text = " | ".join(description_parts)
            ET.SubElement(item, "pubDate").text = menu_item.scraped_at
            
            if menu_item.restaurant_url:
                ET.SubElement(item, "link").text = menu_item.restaurant_url
            
            # Add custom elements for structured data
            ET.SubElement(item, "category").text = menu_item.category or "Menu"
        
        # Write RSS to file
        tree = ET.ElementTree(rss)
        ET.indent(tree, space="  ", level=0)
        tree.write(output_file, encoding='utf-8', xml_declaration=True)
        
        logger.info(f"Exported {len(menu_items)} menu items to RSS: {output_file}")
    
    @staticmethod
    def to_nlweb_json(menu_items: List[MenuItem], output_file: str, html_content: Optional[str] = None, url: str = ""):
        """Export in format optimized for NLWeb ingestion"""
        documents = []
        
        if menu_items:
            # Create individual documents for menu items
            for item in menu_items:
                doc = {
                    "id": f"{item.restaurant_name}_{item.name}".replace(" ", "_").lower(),
                    "title": item.name,
                    "content": f"{item.name}\n\n{item.description}",
                    "metadata": {
                        "type": "menu_item",
                        "restaurant": item.restaurant_name,
                        "category": item.category,
                        "price": item.price,
                        "dietary_info": item.dietary_info,
                        "allergens": item.allergens,
                        "image_url": item.image_url,
                        "source_url": item.restaurant_url,
                        "scraped_at": item.scraped_at
                    },
                    "url": item.restaurant_url,
                    "schema_json": json.dumps(asdict(item))
                }
                documents.append(doc)
                
        elif html_content:
            # Create single document for non-menu page
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else urlparse(url).path
            
            # Extract main content (remove scripts, styles, nav, footer)
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Get text content
            text_content = soup.get_text()
            # Clean up whitespace
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            content = ' '.join(chunk for chunk in chunks if chunk)
            
            # Limit content length if too long
            if len(content) > 10000:
                content = content[:10000] + "..."
            
            doc = {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, url)),
                "title": title,
                "content": content,
                "metadata": {
                    "type": "webpage",
                    "source_url": url,
                    "scraped_at": datetime.now().isoformat(),
                    "content_type": "full_page"
                },
                "url": url,
                "schema_json": json.dumps({"url": url, "title": title, "scraped_at": datetime.now().isoformat()})
            }
            documents.append(doc)
        
        output_data = {
            "documents": documents,
            "total": len(documents),
            "source": "restaurant_menu_scraper",
            "created_at": datetime.now().isoformat(),
            "content_type": "menu_items" if menu_items else "webpage"
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        content_desc = f"{len(menu_items)} menu items" if menu_items else "1 webpage document"
        logger.info(f"Exported {content_desc} for NLWeb ingestion: {output_file}")

async def main():
    parser = argparse.ArgumentParser(
        description="Scrape restaurant menu and export to structured formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://restaurant.com --format nlweb
      Export menu as NLWeb-compatible JSON (default)
  
  %(prog)s https://restaurant.com --format rss --output menu.rss
      Export menu as RSS feed
  
  %(prog)s https://restaurant.com --format nlweb
      Export individual menu items or full page content for NLWeb
        """
    )
    
    parser.add_argument("url", help="Restaurant website URL")
    parser.add_argument("--format", choices=["nlweb", "rss"], 
                       default="nlweb", help="Output format (default: nlweb)")
    parser.add_argument("--output", default=None,
                       help="Output file (default: auto-generated)")
    parser.add_argument("--max-retries", type=int, default=3,
                       help="Maximum retries for failed requests")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Generate output filename if not provided
    if not args.output:
        domain = urlparse(args.url).netloc.replace('.', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = "json" if args.format == "nlweb" else args.format
        args.output = f"{domain}_{timestamp}.{extension}"
    
    # Initialize scraper
    scraper = RestaurantMenuScraper(max_retries=args.max_retries)
    
    # Scrape menu or page content
    menu_items, html_content = await scraper.scrape_menu(args.url)
    
    # Export in requested format
    exporter = MenuDataExporter()
    
    if args.format == "nlweb":
        exporter.to_nlweb_json(menu_items, args.output, html_content, args.url)
    elif args.format == "rss":
        if not menu_items:
            logger.error("RSS format only supports menu items, but no menu items were found!")
            logger.info("Use --format nlweb to export non-menu pages")
            sys.exit(1)
        restaurant_name = menu_items[0].restaurant_name if menu_items else "Restaurant Menu"
        exporter.to_rss(menu_items, args.output, restaurant_name)
    
    print(f"\nScraping completed successfully!")
    
    if menu_items:
        print(f"Found {len(menu_items)} menu items")
        print(f"Output saved to: {args.output}")
        
        # Show sample items
        print(f"\nSample menu items:")
        for i, item in enumerate(menu_items[:2]):
            print(f"{i+1}. {item.name}")
            if item.price:
                print(f"   Price: {item.price}")
            if item.category:
                print(f"   Category: {item.category}")
            if item.description:
                print(f"   Description: {item.description[:100]}...")
            print()
    else:
        print("No menu items found - exported page content as single document")
        print(f"Output saved to: {args.output}")

if __name__ == "__main__":
    asyncio.run(main())