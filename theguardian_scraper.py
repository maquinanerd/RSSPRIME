"""
Scraper for The Guardian (theguardian.com)
"""

import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class TheGuardianScraper(BaseScraper):
    """Scraper for The Guardian"""

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "theguardian.com"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from The Guardian listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # Links have a 'data-link-name="article"' attribute
        for link_tag in soup.find_all('a', {'data-link-name': 'article'}, href=True):
            href = link_tag['href']
            if href.startswith('http') and 'theguardian.com' in href:
                links.add(href)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Find the next page URL from pagination"""
        soup = BeautifulSoup(html, 'lxml')
        next_link = soup.find('a', {'rel': 'next', 'href': True})
        if next_link:
            return urljoin(current_url, next_link['href'])
        return None