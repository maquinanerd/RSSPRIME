"""
Scraper for Fox Sports (foxsports.com)
"""

import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class FoxSportsScraper(BaseScraper):
    """Scraper for Fox Sports"""

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "foxsports.com"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from Fox Sports listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # Main article links are in <a> tags with href starting with /stories/
        for link_tag in soup.select('a[href^="/stories/"]'):
            href = link_tag['href']
            full_url = urljoin(base_url, href)
            links.add(full_url)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Fox Sports uses a 'LOAD MORE' button (JS-driven)."""
        logger.info("FoxSports.com scraper does not support pagination (JS-driven).")
        return None