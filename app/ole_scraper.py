import logging
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


OLE_BASE_URL = "https://www.ole.com.ar"

SECTION_PATHS = {
    "primera": "/futbol-primera",
    "ascenso": "/futbol-ascenso",
}


class OleScraper(BaseScraper):
    """
    Scraper for Ole.com.ar news.
    """

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "ole.com.ar"

    def extract_article_links(self, html, base_url, section=None):
        """
        Extracts article links from the Olé listing page.
        1. Prioritizes JSON-LD (CollectionPage/ItemList) for stability.
        2. Falls back to resilient CSS selectors.
        3. Filters by section and normalizes URLs.
        """
        soup = BeautifulSoup(html, 'lxml')
        raw_links = []
        
        # 1. JSON-LD (Primary, robust method)
        try:
            for tag in soup.find_all("script", {"type": "application/ld+json"}):
                # Using tag.string is safer than .text
                data = json.loads(tag.string or "{}")
                payloads = data if isinstance(data, list) else [data]
                
                for obj in payloads:
                    item_lists = []
                    # Handle CollectionPage -> mainEntity -> ItemList
                    if obj.get("@type") == "CollectionPage":
                        main_entity = obj.get("mainEntity", [])
                        main_entity = [main_entity] if isinstance(main_entity, dict) else main_entity
                        for entity in main_entity:
                            if entity.get("@type") == "ItemList":
                                item_lists.append(entity)
                    # Handle direct ItemList
                    elif obj.get("@type") == "ItemList":
                        item_lists.append(obj)

                    for item_list in item_lists:
                        elements = item_list.get("itemListElement", [])
                        for li in elements:
                            if isinstance(li, dict):
                                url = li.get("url")
                                if not url:
                                    # Fallback for nested item structure like {"item": {"url": "..."}}
                                    url = (li.get("item") or {}).get("url")
                                if url:
                                    raw_links.append(url)
            if raw_links:
                logger.info(f"Successfully extracted {len(raw_links)} links via JSON-LD from {base_url}")

        except Exception as e:
            logger.warning(f"Could not parse JSON-LD from {base_url}, will use CSS fallback. Error: {e}")
            raw_links = [] # Clear any partial results if an error occurred

        # 2. CSS Fallback (if JSON-LD fails or finds nothing)
        if not raw_links:
            logger.info(f"JSON-LD extraction failed or yielded no links for {base_url}. Falling back to CSS selectors.")
            selectors = [
                'article a[href]',
                '.card a[href]',
                '.mod-note a[href]',
            ]
            for sel in selectors:
                for a_tag in soup.select(sel):
                    href = a_tag.get("href")
                    if href:
                        raw_links.append(href)

        # 3. Normalization, Filtering, and Deduplication
        final_links = set()
        expected_path = SECTION_PATHS.get(section, "")
        
        for link in raw_links:
            full_url = urljoin(OLE_BASE_URL, link)
            
            # Ensure it's a valid article URL for the section and filter by path
            if full_url.endswith('.html') and (not expected_path or expected_path in full_url):
                final_links.add(full_url)

        logger.info(f"Extracted {len(final_links)} unique article links from {base_url} for section '{section}'")
        if not final_links:
            logger.warning(f"No article links found for ole/{section} on page {base_url}")
            
        return list(final_links)

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        logger.info("OleScraper does not support pagination.")
        return None