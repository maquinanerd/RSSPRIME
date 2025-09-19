"""
Scraper for Kicker.de
"""

import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class KickerScraper(BaseScraper):
    """Scraper for Kicker.de"""

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "kicker.de"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from Kicker listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # Links are in <a> tags with class 'kick__card-headline-link'
        for link_tag in soup.select('a.kick__card-headline-link'):
            href = link_tag['href']
            full_url = urljoin(base_url, href)
            if full_url.endswith('.html'):
                links.add(full_url)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Kicker start pages do not have standard pagination."""
        logger.info("Kicker.de scraper does not support pagination on start pages.")
        return None