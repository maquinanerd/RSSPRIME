"""
Scraper for La Gazzetta dello Sport (gazzetta.it)
"""

import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class GazzettaScraper(BaseScraper):
    """Scraper for La Gazzetta dello Sport"""

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "gazzetta.it"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from Gazzetta listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # Links are in <h3><a> inside divs with class 'bck-media-text'
        for item in soup.select('div.bck-media-text h3 a[href]'):
            href = item['href']
            full_url = urljoin(base_url, href)
            if 'gazzetta.it' in full_url:
                links.add(full_url)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Gazzetta.it uses JS-driven pagination."""
        logger.info("Gazzetta.it scraper does not support pagination (JS-driven).")
        return None