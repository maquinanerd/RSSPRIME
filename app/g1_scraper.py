"""
G1 (g1.globo.com) scraper
"""

import json
import logging
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class G1Scraper(BaseScraper):
    """Scraper for G1 (g1.globo.com)"""

    def __init__(self, store, request_delay=1.0):
        super().__init__(store, request_delay)
        # Use more browser-like headers for G1 to avoid potential blocks
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Referer': 'https://www.google.com/',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        })

    def get_site_domain(self):
        return "g1.globo.com"

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    def _fetch_page(self, url):
        """Override to use enhanced browser headers and add resilience for G1."""
        if not self.can_fetch(url):
            logger.warning(f"Robots.txt disallows fetching {url}")
            return None
        
        try:
            # The headers are already in self.session from __init__
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Check for minimal content to detect soft blocks or JS-only pages
            if not response.text or len(response.text) < 5000: # G1 pages are usually large
                logger.warning(f"Received minimal content for {url} (len: {len(response.text)}). Possible block or JS-heavy page.")
            
            return response.text
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e.response.status_code}. The scraper is likely being blocked.")
            raise
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from G1 pages"""
        if not html:
            logger.warning("HTML content is empty, cannot extract links.")
            return []

        links = []
        soup = BeautifulSoup(html, 'lxml')
        seen = set()

        # --- METHOD 1: JSON-LD (Most Reliable) ---
        # G1 provides a structured data script which is the best source for links.
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                # Data can be a single object or a list of objects. Find the ItemList.
                item_list_data = None
                if isinstance(data, list):
                    item_list_data = next((item for item in data if item.get('@type') == 'ItemList'), None)
                elif isinstance(data, dict) and data.get('@type') == 'ItemList':
                    item_list_data = data

                if item_list_data and 'itemListElement' in item_list_data:
                    for item in item_list_data['itemListElement']:
                        url = item.get('url')
                        if url and self._is_valid_article_url(url, section):
                            full_url = urljoin(base_url, url)
                            if full_url not in seen:
                                links.append(full_url)
                                seen.add(full_url)
                    
                    if links:
                        logger.info(f"Found {len(links)} links via JSON-LD for section '{section}'.")
                        return links  # Success!

            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"Could not parse JSON-LD script: {e}. Trying next script or falling back.")
                continue

        # --- METHOD 2: HTML Fallback (Less Reliable) ---
        logger.warning(f"JSON-LD method failed for section '{section}'. Falling back to broad HTML link search.")
        for element in soup.find_all('a', href=True):
            href = element.get('href')
            if href and self._is_valid_article_url(href, section):
                full_url = urljoin(base_url, href)
                if full_url not in seen:
                    links.append(full_url)
                    seen.add(full_url)

        if not links:
            logger.error(f"FATAL: No links found for G1 section '{section}' using any method. The scraper is likely blocked or the page structure has completely changed.")
        else:
            logger.info(f"Found {len(links)} links via HTML fallback for section '{section}'")

        return links

    def _is_valid_article_url(self, url, section=None):
        """Check if URL is a valid G1 article"""
        if not url:
            return False

        try:
            parsed_url = urlparse(url)
            path = parsed_url.path
        except Exception:
            return False

        if 'g1.globo.com' not in url and not url.startswith('/'):
            return False

        exclude_patterns = ['/video/', '/ao-vivo/', '/index.ghtml', 'javascript:', 'mailto:', '#']
        if any(pattern in url for pattern in exclude_patterns):
            return False
        
        if not path.endswith('.ghtml'):
            return False

        if section:
            # Check if the path correctly corresponds to the section.
            # The path should start with the section name.
            # Example: /economia/noticia/... for section 'economia'
            
            path_segments = path.strip('/').split('/')
            if not path_segments:
                return False

            # Handle special case for 'agronegocios' which is a sub-section of 'economia'
            if section == 'agronegocios' and (len(path_segments) < 2 or path_segments[0] != 'economia' or path_segments[1] != 'agronegocios'):
                return False
            elif section == 'economia' and (path_segments[0] != 'economia' or (len(path_segments) > 1 and path_segments[1] == 'agronegocios')):
                return False # Must be 'economia' but not 'agronegocios'
            elif section not in ['economia', 'agronegocios'] and path_segments[0] != section:
                return False # For other sections like 'politica'
        
        return True

    def find_next_page_url(self, html, current_url):
        """G1 uses a JSON endpoint for pagination, which is not supported. Disable it."""
        logger.debug("G1 pagination is not supported (uses JSON). Scraping first page only.")
        return None